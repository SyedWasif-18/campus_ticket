from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import CustomUser
from .forms import CustomUserCreationForm, ProfileUpdateForm
from .decorators import admin_required

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('dashboard:index')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    if request.method == 'POST' or request.method == 'GET':  # Support both for ease of use
        auth_logout(request)
        messages.info(request, "You have been logged out.")
    return redirect('accounts:login')

@login_required
def profile_view(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated successfully!")
            return redirect('accounts:profile')
    else:
        form = ProfileUpdateForm(instance=request.user)
    
    return render(request, 'accounts/profile.html', {'form': form})

# Admin specific User Management Views
@login_required
@admin_required
def manage_users(request):
    role_filter = request.GET.get('role', '')
    users = CustomUser.objects.exclude(role='ADMIN').order_by('username')
    
    if role_filter:
        users = users.filter(role=role_filter)
        
    paginator = Paginator(users, 10)  # Show 10 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'accounts/manage_users.html', {
        'page_obj': page_obj,
        'role_filter': role_filter
    })

@login_required
@admin_required
def create_user(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"User {user.username} has been created successfully!")
            return redirect('accounts:manage_users')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Create User'})

@login_required
@admin_required
def edit_user(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    if request.method == 'POST':
        # Since CustomUserCreationForm inherits from UserCreationForm (which hashes passwords),
        # we will write a custom view logic or update using a model form for simplicity.
        # But we can also change username, email, phone number, role, department directly.
        from .forms import CustomUserChangeForm
        form = CustomUserChangeForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f"User {user.username} has been updated successfully!")
            return redirect('accounts:manage_users')
    else:
        from .forms import CustomUserChangeForm
        form = CustomUserChangeForm(instance=user)
    
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Edit User'})

@login_required
@admin_required
def delete_user(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f"User {username} deleted successfully!")
        return redirect('accounts:manage_users')
    return render(request, 'accounts/user_confirm_delete.html', {'user_to_delete': user})

