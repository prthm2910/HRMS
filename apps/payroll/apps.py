import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class PayrollConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.payroll'
    verbose_name = 'Payroll & Compensation'

    def ready(self):
        logger.info("Payroll application ready | Context: Compensation & Benefits")
