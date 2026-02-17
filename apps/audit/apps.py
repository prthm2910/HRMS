import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.audit'
    label = 'audit'  # App label for model references
    
    def ready(self):
        # This checks if the signals file exists and loads it into memory
        import apps.audit.signals
        logger.info("Audit app ready | Signals and configurations loaded.")