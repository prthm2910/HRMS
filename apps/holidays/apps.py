from django.apps import AppConfig


class HolidaysConfig(AppConfig):
    name = 'apps.holidays'
    label = 'holidays'
    default_auto_field = 'django.db.models.BigAutoField'
    
    def ready(self):
        """Import signals when app is ready"""
        import apps.holidays.signals
