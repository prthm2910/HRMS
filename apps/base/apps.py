from django.apps import AppConfig


class BaseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.base'
    label = 'base'  # App label for model references
    
    def ready(self):
        """Import signals when app is ready"""
        import apps.base.signals  # noqa
