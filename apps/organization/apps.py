import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)

class OrganizationConfig(AppConfig):  # Renamed from EmployeesConfig
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.organization'

    def ready(self):
        logger.info("Organization app ready | Core structural models initialized.")
             # Renamed from 'employees'
    label = 'organization'  # App label for model references