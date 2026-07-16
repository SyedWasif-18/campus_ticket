from django.db import models
from django.conf import settings
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

class Room(models.Model):
    room_number = models.CharField(max_length=50, unique=True)
    floor = models.CharField(max_length=50)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='rooms')
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)

    def __str__(self):
        return f"Room {self.room_number} - {self.department.code} (Floor {self.floor})"

    def save(self, *args, **kwargs):
        # Save first to ensure we have an ID
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new or not self.qr_code:
            # We construct a URL pointing to the ticket creation page with the pre-filled room_id.
            # During local development, this resolves to localhost.
            qr_data = f"/tickets/raise/?room_id={self.id}"
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            
            filename = f"room_{self.room_number}_qr.png"
            self.qr_code.save(filename, ContentFile(buffer.getvalue()), save=False)
            
            # Save again to write the qr_code path to the DB
            super().save(update_fields=['qr_code'])

class Ticket(models.Model):
    CATEGORY_CHOICES = (
        ('SUPPLIES', 'Classroom Supplies'),
        ('TECHNICAL', 'Technical Issues'),
        ('MAINTENANCE', 'Maintenance'),
    )

    SUB_CATEGORY_CHOICES = (
        # Classroom Supplies
        ('Chalk', 'Chalk'),
        ('Duster', 'Duster'),
        ('Marker', 'Marker'),
        ('White Paper', 'White Paper'),
        
        # Technical Issues
        ('Projector', 'Projector'),
        ('Microphone', 'Microphone'),
        ('Speaker', 'Speaker'),
        ('Smart Board', 'Smart Board'),
        ('Computer', 'Computer'),
        ('Internet', 'Internet'),
        
        # Maintenance
        ('Fan', 'Fan'),
        ('Lights', 'Lights'),
        ('Door', 'Door'),
        ('Bench', 'Bench'),
        ('Water Leakage', 'Water Leakage'),
    )

    PRIORITY_CHOICES = (
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('EMERGENCY', 'Emergency'),
    )

    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )

    faculty = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='raised_tickets'
    )
    attender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets'
    )
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='tickets')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    sub_category = models.CharField(max_length=50, choices=SUB_CATEGORY_CHOICES)
    priority = models.CharField(max_length=15, choices=PRIORITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    description = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ticket #{self.id} - {self.sub_category} ({self.status})"

    class Meta:
        ordering = ['-created_at']

    @property
    def response_time_seconds(self):
        """Time from creation to acceptance"""
        if self.accepted_at:
            return (self.accepted_at - self.created_at).total_seconds()
        return None

    @property
    def resolution_time_seconds(self):
        """Time from acceptance to completion"""
        if self.completed_at and self.accepted_at:
            return (self.completed_at - self.accepted_at).total_seconds()
        return None

class Rating(models.Model):
    SCORE_CHOICES = [(i, str(i)) for i in range(1, 6)]

    ticket = models.OneToOneField(Ticket, on_delete=models.CASCADE, related_name='rating')
    score = models.IntegerField(choices=SCORE_CHOICES)
    comments = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rating {self.score}/5 for Ticket #{self.ticket.id}"

