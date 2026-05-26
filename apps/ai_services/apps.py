from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class AiServicesConfig(AppConfig):
    """
    Django app configuration for AI Services.
    
    This app provides AI/ML capabilities like OCR, NLP, and computer vision
    that can be consumed by other apps in the HRMS system.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ai_services'
    verbose_name = 'AI Services'

    def ready(self):
        """
        Signals that the application is ready and performs initialization tasks.
        """
        logger.info("AI Services app ready | Configurations initialized.")
