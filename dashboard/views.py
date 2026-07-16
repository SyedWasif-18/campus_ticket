from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Avg, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
import csv
import json
from datetime import timedelta

from tickets.models import Ticket, Department, Rating
from notifications.models import Notification
from accounts.models import CustomUser
from accounts.decorators import admin_required


@login_required
def index(request):
    """Smart redirect to role-specific dashboard."""
    user = request.user
    if user.role == 'ADMIN' or user.is_superuser:
        return redirect('dashboard:admin_dashboard')
    elif user.role == 'ATTENDER':
        return redirect('dashboard:attender_dashboard')
    else:
        return redirect('dashboard:faculty_dashboard')


# ─────────────────────────── FACULTY DASHBOARD ──────────────────────────────

@login_required
def faculty_dashboard(request):
    """Faculty view: see tickets they have raised, filtered by status."""
    if request.user.role not in ('FACULTY',) and not request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect('dashboard:index')

    tickets = Ticket.objects.filter(faculty=request.user).order_by('-created_at')

    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        tickets = tickets.filter(status=status_filter)

    # KPI counts for the current user
    kpi = {
        'total': Ticket.objects.filter(faculty=request.user).count(),
        'pending': Ticket.objects.filter(faculty=request.user, status='PENDING').count(),
        'in_progress': Ticket.objects.filter(faculty=request.user, status__in=['ACCEPTED', 'IN_PROGRESS']).count(),
        'completed': Ticket.objects.filter(faculty=request.user, status='COMPLETED').count(),
        'cancelled': Ticket.objects.filter(faculty=request.user, status='CANCELLED').count(),
    }

    # Unread notifications count
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    recent_notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:5]

    return render(request, 'dashboard/faculty.html', {
        'tickets': tickets[:20],
        'kpi': kpi,
        'status_filter': status_filter,
        'status_choices': Ticket.STATUS_CHOICES,
        'unread_count': unread_count,
        'recent_notifications': recent_notifications,
    })


# ─────────────────────────── ATTENDER DASHBOARD ─────────────────────────────

@login_required
def attender_dashboard(request):
    """Attender view: live feed of pending department tickets + their active ones."""
    if request.user.role not in ('ATTENDER',) and not request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect('dashboard:index')

    dept = request.user.department

    # Pending tickets in the attender's department (available to accept)
    pending_tickets = Ticket.objects.filter(
        status='PENDING',
        room__department=dept
    ).order_by('-created_at') if dept else Ticket.objects.none()

    # Tickets this attender has accepted / is working on
    my_tickets = Ticket.objects.filter(
        attender=request.user
    ).exclude(status__in=['CANCELLED']).order_by('-updated_at')

    kpi = {
        'pending_dept': pending_tickets.count(),
        'my_active': my_tickets.filter(status__in=['ACCEPTED', 'IN_PROGRESS']).count(),
        'my_completed': my_tickets.filter(status='COMPLETED').count(),
    }

    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    recent_notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:5]

    return render(request, 'dashboard/attender.html', {
        'pending_tickets': pending_tickets,
        'my_tickets': my_tickets,
        'kpi': kpi,
        'dept': dept,
        'unread_count': unread_count,
        'recent_notifications': recent_notifications,
    })


# ─────────────────────────── ADMIN DASHBOARD ────────────────────────────────

@login_required
@admin_required
def admin_dashboard(request):
    """Admin view: KPI cards, analytics, quick management links."""
    total_tickets = Ticket.objects.count()
    open_tickets = Ticket.objects.filter(status__in=['PENDING', 'ACCEPTED', 'IN_PROGRESS']).count()
    completed_tickets = Ticket.objects.filter(status='COMPLETED').count()
    cancelled_tickets = Ticket.objects.filter(status='CANCELLED').count()

    # Average resolution time (in minutes) for completed tickets
    completed_with_times = Ticket.objects.filter(
        status='COMPLETED',
        completed_at__isnull=False,
        accepted_at__isnull=False
    )
    if completed_with_times.exists():
        total_seconds = sum(t.resolution_time_seconds for t in completed_with_times if t.resolution_time_seconds)
        count = completed_with_times.count()
        avg_resolution_minutes = round(total_seconds / count / 60, 1) if count else 0
    else:
        avg_resolution_minutes = 0

    # Average satisfaction rating
    avg_rating = Rating.objects.aggregate(avg=Avg('score'))['avg']
    avg_rating = round(avg_rating, 1) if avg_rating else 0

    # Top departments by ticket count
    dept_stats = Department.objects.annotate(
        ticket_count=Count('rooms__tickets')
    ).order_by('-ticket_count')[:5]

    # Recent 10 tickets
    recent_tickets = Ticket.objects.select_related('faculty', 'room', 'attender').order_by('-created_at')[:10]

    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()

    kpi = {
        'total': total_tickets,
        'open': open_tickets,
        'completed': completed_tickets,
        'cancelled': cancelled_tickets,
        'avg_resolution': avg_resolution_minutes,
        'avg_rating': avg_rating,
        'total_users': CustomUser.objects.count(),
        'total_departments': Department.objects.count(),
    }

    return render(request, 'dashboard/admin.html', {
        'kpi': kpi,
        'dept_stats': dept_stats,
        'recent_tickets': recent_tickets,
        'unread_count': unread_count,
    })


# ─────────────────────────── AJAX / CHART API ───────────────────────────────

@login_required
@admin_required
def api_tickets_by_status(request):
    """Return ticket counts grouped by status for Chart.js doughnut."""
    data = Ticket.objects.values('status').annotate(count=Count('id'))
    result = {item['status']: item['count'] for item in data}
    return JsonResponse(result)


@login_required
@admin_required
def api_tickets_over_time(request):
    """Return ticket counts grouped by day (last 30 days) for line chart."""
    since = timezone.now() - timedelta(days=30)
    data = (
        Ticket.objects.filter(created_at__gte=since)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    labels = [str(item['day']) for item in data]
    counts = [item['count'] for item in data]
    return JsonResponse({'labels': labels, 'counts': counts})


@login_required
@admin_required
def api_tickets_by_category(request):
    """Return ticket counts grouped by sub_category for bar chart."""
    data = Ticket.objects.values('sub_category').annotate(count=Count('id')).order_by('-count')[:10]
    labels = [item['sub_category'] for item in data]
    counts = [item['count'] for item in data]
    return JsonResponse({'labels': labels, 'counts': counts})


@login_required
@admin_required
def api_rating_distribution(request):
    """Return rating score distribution for Chart.js."""
    data = Rating.objects.values('score').annotate(count=Count('id')).order_by('score')
    result = {str(item['score']): item['count'] for item in data}
    return JsonResponse(result)


# ─────────────────────────── CSV EXPORT ─────────────────────────────────────

@login_required
@admin_required
def export_tickets_csv(request):
    """Stream all tickets as a CSV download."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="tickets_export.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Status', 'Priority', 'Category', 'Sub-Category',
        'Room', 'Department', 'Faculty', 'Attender',
        'Created At', 'Accepted At', 'Completed At',
        'Response Time (min)', 'Resolution Time (min)', 'Rating'
    ])

    tickets = Ticket.objects.select_related(
        'room', 'room__department', 'faculty', 'attender'
    ).order_by('-created_at')

    for t in tickets:
        try:
            rating = t.rating.score
        except Exception:
            rating = ''

        writer.writerow([
            t.id,
            t.get_status_display(),
            t.get_priority_display(),
            t.get_category_display(),
            t.sub_category,
            t.room.room_number,
            t.room.department.name,
            t.faculty.username,
            t.attender.username if t.attender else '',
            t.created_at.strftime('%Y-%m-%d %H:%M'),
            t.accepted_at.strftime('%Y-%m-%d %H:%M') if t.accepted_at else '',
            t.completed_at.strftime('%Y-%m-%d %H:%M') if t.completed_at else '',
            round(t.response_time_seconds / 60, 1) if t.response_time_seconds else '',
            round(t.resolution_time_seconds / 60, 1) if t.resolution_time_seconds else '',
            rating,
        ])

    return response


# ─────────────────────────── NOTIFICATIONS ──────────────────────────────────

@login_required
def notifications_view(request):
    """List all notifications for the current user and mark as read."""
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    # Mark all as read
    notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'dashboard/notifications.html', {'notifications': notifications})


@login_required
def mark_notification_read(request, notif_id):
    """Mark a single notification as read (AJAX)."""
    try:
        notif = Notification.objects.get(id=notif_id, recipient=request.user)
        notif.is_read = True
        notif.save()
        return JsonResponse({'status': 'ok'})
    except Notification.DoesNotExist:
        return JsonResponse({'status': 'error'}, status=404)
