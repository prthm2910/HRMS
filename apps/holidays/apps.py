import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class HolidaysConfig(AppConfig):
    name = 'apps.holidays'
    label = 'holidays'
    default_auto_field = 'django.db.models.BigAutoField'
    
    def ready(self):
        """Import signals when app is ready"""
        import apps.holidays.signals
        logger.info("Holidays app ready | Holiday management signals has been initialized.")
