from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('FACULTY', 'Faculty'),
        ('ATTENDER', 'Attender'),
    )
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='FACULTY')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    # Using a string reference to avoid circular imports with the tickets app
    department = models.ForeignKey(
        'tickets.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_admin_role(self):
        return self.role == 'ADMIN' or self.is_superuser

    @property
    def is_faculty_role(self):
        return self.role == 'FACULTY'

    @property
    def is_attender_role(self):
        return self.role == 'ATTENDER'

