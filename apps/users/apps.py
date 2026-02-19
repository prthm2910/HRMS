import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'
    label = 'users'  # App label for model references (e.g., AUTH_USER_MODEL)

    def ready(self):
        logger.info("Users application ready | Context: Identity & Access Management")
