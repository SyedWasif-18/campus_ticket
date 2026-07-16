from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    name = 'notifications'

    def ready(self):
        # Import signals to ensure they are registered when the app loads
        import notifications.signals
