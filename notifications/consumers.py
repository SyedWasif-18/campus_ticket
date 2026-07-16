import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        
        # Accept only authenticated connections
        if self.user and self.user.is_authenticated:
            self.user_group = f"user_{self.user.id}"
            
            # Join personal group
            await self.channel_layer.group_add(
                self.user_group,
                self.channel_name
            )
            
            # Join department group if the user is an Attender and belongs to a department
            if self.user.role == 'ATTENDER' and self.user.department:
                self.dept_group = f"department_{self.user.department.id}"
                await self.channel_layer.group_add(
                    self.dept_group,
                    self.channel_name
                )
            else:
                self.dept_group = None

            # Join admin group if user is an Admin
            if self.user.role == 'ADMIN' or self.user.is_superuser:
                self.admin_group = "admins"
                await self.channel_layer.group_add(
                    self.admin_group,
                    self.channel_name
                )
            else:
                self.admin_group = None

            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        # Leave groups
        if hasattr(self, 'user_group') and self.user_group:
            await self.channel_layer.group_discard(
                self.user_group,
                self.channel_name
            )
        if hasattr(self, 'dept_group') and self.dept_group:
            await self.channel_layer.group_discard(
                self.dept_group,
                self.channel_name
            )
        if hasattr(self, 'admin_group') and self.admin_group:
            await self.channel_layer.group_discard(
                self.admin_group,
                self.channel_name
            )

    # Receive message from WebSocket (if client sends anything, optional for this workflow)
    async def receive(self, text_data):
        pass

    # Custom helper to receive notifications from channel groups and send to WebSocket client
    async def send_notification(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'ticket_id': event.get('ticket_id'),
            'status': event.get('status'),
            'action': event.get('action'),
        }))
