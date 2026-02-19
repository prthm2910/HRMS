import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class LeavesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.leaves'
    label = 'leaves'  # App label for model references

    def ready(self):
        import apps.leaves.signals
        logger.info("Leaves app ready | Leave management signals has been initialized.")