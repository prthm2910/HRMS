import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class BaseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.base'
    label = 'base'  # App label for model references
    
    def ready(self):
        """Import signals when app is ready"""
        import apps.base.signals
        logger.info("Base app ready | Foundation signals initialized.")
