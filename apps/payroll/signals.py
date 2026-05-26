"""
Signals for the payroll app.
Auto-syncing is disabled in favor of HR-led curation.
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='organization.Employee')
def on_employee_saved(sender, instance, created, **kwargs):
    """
    Log reminders for HR to curate salary structures.
    """
    if created:
        logger.info(
            f"New employee created: {instance.employee_id}. "
            f"Reminder: HR must curate the salary structure for this employee."
        )
    
    # We no longer auto-sync. Curation is handled via the API.
