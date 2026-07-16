from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied

def role_required(allowed_roles):
    """
    Decorator to check if user has one of the allowed roles.
    Raises PermissionDenied if the user is not authorized.
    """
    def check_role(user):
        if not user.is_authenticated:
            return False
        if user.is_superuser or user.role in allowed_roles:
            return True
        raise PermissionDenied
    return user_passes_test(check_role)

def admin_required(function=None, login_url='accounts:login'):
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and (u.is_superuser or u.role == 'ADMIN'),
        login_url=login_url
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

def faculty_required(function=None, login_url='accounts:login'):
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.role == 'FACULTY',
        login_url=login_url
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

def attender_required(function=None, login_url='accounts:login'):
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.role == 'ATTENDER',
        login_url=login_url
    )
    if function:
        return actual_decorator(function)
    return actual_decorator
