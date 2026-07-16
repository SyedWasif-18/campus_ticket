from django.db.models.signals import post_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from tickets.models import Ticket
from .models import Notification
from accounts.models import CustomUser

@receiver(post_save, sender=Ticket)
def ticket_notification_handler(sender, instance, created, **kwargs):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
        
    room = instance.room
    dept = room.department
    faculty = instance.faculty
    attender = instance.attender
    
    if created:
        # 1. Ticket Created: Notify all Attenders of the Room's Department
        message = f"New ticket raised: Room {room.room_number} needs '{instance.get_sub_category_display()}' (Priority: {instance.get_priority_display()})."
        
        # Save persistent notification in database for each attender in the department
        attenders = CustomUser.objects.filter(role='ATTENDER', department=dept)
        notifications = [
            Notification(recipient=att, ticket=instance, message=message)
            for att in attenders
        ]
        Notification.objects.bulk_create(notifications)
        
        # Broadcast to the department group (for real-time dashboard updates & notifications)
        async_to_sync(channel_layer.group_send)(
            f"department_{dept.id}",
            {
                "type": "send_notification",
                "message": message,
                "ticket_id": instance.id,
                "status": instance.status,
                "action": "CREATE",
                "ticket_data": {
                    "id": instance.id,
                    "category_class": instance.category.lower(),
                    "sub_category": instance.get_sub_category_display(),
                    "description": instance.description or "",
                    "room_number": room.room_number,
                    "priority_class": instance.priority.lower(),
                    "priority_display": instance.get_priority_display(),
                    "faculty_name": faculty.get_full_name() or faculty.username,
                }
            }
        )
        
        # Also broadcast to admins
        async_to_sync(channel_layer.group_send)(
            "admins",
            {
                "type": "send_notification",
                "message": f"New ticket #{instance.id} raised in room {room.room_number}.",
                "ticket_id": instance.id,
                "status": instance.status,
                "action": "CREATE"
            }
        )
        
    else:
        # 2. Ticket Updated: Check status changes
        # We can detect state transitions
        message = ""
        recipient = None
        action = "UPDATE"
        
        if instance.status == 'ACCEPTED' and attender:
            message = f"Your ticket #{instance.id} ({instance.get_sub_category_display()}) in Room {room.room_number} has been accepted by {attender.username}."
            recipient = faculty
            action = "ACCEPT"
            
            # Also notify the department attenders that the ticket has been taken (to lock/remove from pending list)
            async_to_sync(channel_layer.group_send)(
                f"department_{dept.id}",
                {
                    "type": "send_notification",
                    "message": f"Ticket #{instance.id} is accepted by {attender.username}.",
                    "ticket_id": instance.id,
                    "status": instance.status,
                    "action": "LOCK"
                }
            )
            
        elif instance.status == 'IN_PROGRESS' and attender:
            message = f"Your ticket #{instance.id} ({instance.get_sub_category_display()}) in Room {room.room_number} is now in progress."
            recipient = faculty
            action = "IN_PROGRESS"
            
        elif instance.status == 'COMPLETED':
            message = f"Your ticket #{instance.id} ({instance.get_sub_category_display()}) in Room {room.room_number} has been completed! Please rate the service."
            recipient = faculty
            action = "COMPLETE"
            
        elif instance.status == 'CANCELLED':
            message = f"Ticket #{instance.id} in Room {room.room_number} has been cancelled by the faculty member."
            action = "CANCEL"
            # If an attender had already accepted it, notify them directly
            if attender:
                recipient = attender
            else:
                # Otherwise, notify all department attenders that it was cancelled
                async_to_sync(channel_layer.group_send)(
                    f"department_{dept.id}",
                    {
                        "type": "send_notification",
                        "message": message,
                        "ticket_id": instance.id,
                        "status": instance.status,
                        "action": "CANCEL"
                    }
                )
                
        if recipient and message:
            # Create persistent database record for recipient
            Notification.objects.create(recipient=recipient, ticket=instance, message=message)
            
            # Send WebSocket notification to the user's personal group
            async_to_sync(channel_layer.group_send)(
                f"user_{recipient.id}",
                {
                    "type": "send_notification",
                    "message": message,
                    "ticket_id": instance.id,
                    "status": instance.status,
                    "action": action
                }
            )

        # Notify admins of status updates
        async_to_sync(channel_layer.group_send)(
            "admins",
            {
                "type": "send_notification",
                "message": f"Ticket #{instance.id} status changed to {instance.get_status_display()}.",
                "ticket_id": instance.id,
                "status": instance.status,
                "action": action
            }
        )
