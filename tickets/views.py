from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import HttpResponse, Http404
import zipfile
from io import BytesIO

from .models import Department, Room, Ticket, Rating
from .forms import TicketForm, RatingForm, DepartmentForm, RoomForm
from accounts.decorators import admin_required, faculty_required, attender_required

@login_required
@faculty_required
def raise_ticket(request):
    room_id = request.GET.get('room_id')
    initial_data = {}
    
    if room_id:
        try:
            room = Room.objects.get(id=room_id)
            initial_data['room'] = room
            initial_data['department'] = room.department
        except Room.DoesNotExist:
            messages.warning(request, "Scanned QR code did not match a valid room. Please select manually.")

    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.faculty = request.user
            ticket.status = 'PENDING'
            ticket.save()
            messages.success(request, f"Ticket #{ticket.id} raised successfully! Department attenders have been notified.")
            return redirect('dashboard:index')
        else:
            messages.error(request, "Failed to submit ticket. Please check the details.")
    else:
        form = TicketForm(initial=initial_data)
        
    return render(request, 'tickets/raise_ticket.html', {
        'form': form,
        'room_id': room_id
    })

@login_required
@faculty_required
def cancel_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id, faculty=request.user)
    if ticket.status == 'PENDING':
        ticket.status = 'CANCELLED'
        ticket.save()
        messages.success(request, f"Ticket #{ticket.id} has been cancelled.")
    else:
        messages.error(request, "You can only cancel tickets that are still pending.")
    return redirect('tickets:ticket_detail', ticket_id=ticket.id)

@login_required
@attender_required
def accept_ticket(request, ticket_id):
    # Atomic transaction with database-level row locking to prevent multiple attenders from accepting simultaneously
    with transaction.atomic():
        try:
            ticket = Ticket.objects.select_for_update().get(id=ticket_id)
        except Ticket.DoesNotExist:
            raise Http404("Ticket does not exist")
            
        if ticket.status == 'PENDING':
            # Check if attender is of the same department (or admin)
            if request.user.department == ticket.room.department or request.user.is_superuser:
                ticket.status = 'ACCEPTED'
                ticket.attender = request.user
                ticket.accepted_at = timezone.now()
                ticket.save()
                messages.success(request, f"You have accepted Ticket #{ticket.id}. It is now assigned to you.")
            else:
                messages.error(request, "You can only accept tickets from your assigned department.")
        else:
            messages.error(request, f"Ticket #{ticket.id} has already been accepted/resolved by another user.")
            
    return redirect('dashboard:index')

@login_required
@attender_required
def update_ticket_status(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id, attender=request.user)
    new_status = request.POST.get('status')
    
    if new_status in ['IN_PROGRESS', 'COMPLETED']:
        ticket.status = new_status
        if new_status == 'COMPLETED':
            ticket.completed_at = timezone.now()
        ticket.save()
        messages.success(request, f"Ticket #{ticket.id} status updated to {ticket.get_status_display()}.")
    else:
        messages.error(request, "Invalid status transition.")
        
    return redirect('tickets:ticket_detail', ticket_id=ticket.id)

@login_required
def ticket_detail(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    # Permission check: Faculty can only see their own tickets, Attender can see their department/assigned, Admin can see all
    if request.user.role == 'FACULTY' and ticket.faculty != request.user:
        messages.error(request, "You do not have permission to view this ticket.")
        return redirect('dashboard:index')
    elif request.user.role == 'ATTENDER' and ticket.room.department != request.user.department and ticket.attender != request.user:
        messages.error(request, "You do not have permission to view this ticket.")
        return redirect('dashboard:index')
        
    rating_form = None
    if ticket.status == 'COMPLETED' and not hasattr(ticket, 'rating') and request.user == ticket.faculty:
        rating_form = RatingForm()
        
    return render(request, 'tickets/ticket_detail.html', {
        'ticket': ticket,
        'rating_form': rating_form
    })

@login_required
def ticket_list(request):
    queryset = Ticket.objects.all()
    
    # Filter by user role
    if request.user.role == 'FACULTY':
        queryset = queryset.filter(faculty=request.user)
    elif request.user.role == 'ATTENDER':
        # Attenders see their assigned tickets, or pending tickets in their department
        queryset = queryset.filter(Q(attender=request.user) | Q(status='PENDING', room__department=request.user.department))
    
    # Search and Filter Parameters
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    dept_filter = request.GET.get('department', '')
    priority_filter = request.GET.get('priority', '')
    date_filter = request.GET.get('date', '')
    
    if search_query:
        queryset = queryset.filter(
            Q(description__icontains=search_query) |
            Q(room__room_number__icontains=search_query) |
            Q(sub_category__icontains=search_query)
        )
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if dept_filter:
        queryset = queryset.filter(room__department_id=dept_filter)
    if priority_filter:
        queryset = queryset.filter(priority=priority_filter)
    if date_filter:
        queryset = queryset.filter(created_at__date=date_filter)
        
    # Order by creation date
    queryset = queryset.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    departments = Department.objects.all()
    
    return render(request, 'tickets/ticket_list.html', {
        'page_obj': page_obj,
        'departments': departments,
        'search_query': search_query,
        'status_filter': status_filter,
        'dept_filter': dept_filter,
        'priority_filter': priority_filter,
        'date_filter': date_filter,
        'status_choices': Ticket.STATUS_CHOICES,
        'priority_choices': Ticket.PRIORITY_CHOICES,
    })

@login_required
@faculty_required
def submit_rating(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id, faculty=request.user, status='COMPLETED')
    if request.method == 'POST':
        form = RatingForm(request.POST)
        if form.is_valid():
            rating = form.save(commit=False)
            rating.ticket = ticket
            rating.save()
            messages.success(request, "Thank you for your feedback!")
        else:
            messages.error(request, "Invalid rating submission.")
    return redirect('tickets:ticket_detail', ticket_id=ticket.id)

# Department Management (Admin)
@login_required
@admin_required
def manage_departments(request):
    departments = Department.objects.all().order_by('name')
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Department added successfully!")
            return redirect('tickets:manage_departments')
    else:
        form = DepartmentForm()
        
    return render(request, 'tickets/manage_departments.html', {
        'departments': departments,
        'form': form
    })

@login_required
@admin_required
def edit_department(request, dept_id):
    dept = get_object_or_404(Department, id=dept_id)
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=dept)
        if form.is_valid():
            form.save()
            messages.success(request, "Department updated successfully!")
            return redirect('tickets:manage_departments')
    else:
        form = DepartmentForm(instance=dept)
    return render(request, 'tickets/dept_form.html', {'form': form, 'title': 'Edit Department'})

@login_required
@admin_required
def delete_department(request, dept_id):
    dept = get_object_or_404(Department, id=dept_id)
    if request.method == 'POST':
        name = dept.name
        dept.delete()
        messages.success(request, f"Department '{name}' deleted successfully!")
        return redirect('tickets:manage_departments')
    return render(request, 'tickets/dept_confirm_delete.html', {'dept': dept})

# Room Management (Admin)
@login_required
@admin_required
def manage_rooms(request):
    rooms = Room.objects.all().order_by('room_number')
    if request.method == 'POST':
        form = RoomForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Room added successfully with auto-generated QR code!")
            return redirect('tickets:manage_rooms')
    else:
        form = RoomForm()
        
    return render(request, 'tickets/manage_rooms.html', {
        'rooms': rooms,
        'form': form
    })

@login_required
@admin_required
def edit_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    if request.method == 'POST':
        form = RoomForm(request.POST, instance=room)
        if form.is_valid():
            form.save()
            messages.success(request, "Room updated successfully!")
            return redirect('tickets:manage_rooms')
    else:
        form = RoomForm(instance=room)
    return render(request, 'tickets/room_form.html', {'form': form, 'title': 'Edit Room'})

@login_required
@admin_required
def delete_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    if request.method == 'POST':
        room_number = room.room_number
        room.delete()
        messages.success(request, f"Room '{room_number}' deleted successfully!")
        return redirect('tickets:manage_rooms')
    return render(request, 'tickets/room_confirm_delete.html', {'room': room})

@login_required
@admin_required
def download_qr(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    if not room.qr_code:
        # Re-save to generate QR if missing
        room.save()
    
    response = HttpResponse(room.qr_code, content_type="image/png")
    response['Content-Disposition'] = f'attachment; filename="room_{room.room_number}_qr.png"'
    return response

@login_required
@admin_required
def download_all_qrs(request):
    rooms = Room.objects.all()
    if not rooms.exists():
        messages.warning(request, "No rooms exist to generate QR codes.")
        return redirect('tickets:manage_rooms')
        
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for room in rooms:
            if not room.qr_code:
                room.save()
            
            if room.qr_code:
                try:
                    # Reset pointer in case it was read previously
                    room.qr_code.open('rb')
                    filename = f"room_{room.room_number}_qr.png"
                    zip_file.writestr(filename, room.qr_code.read())
                    room.qr_code.close()
                except Exception as e:
                    pass
                
    response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="all_room_qrs.zip"'
    return response

