from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'audit'
    def ready(self):
        # This checks if the signals file exists and loads it into memory
        import audit.signals