"""
Signals for auto-syncing EmployeeSalaryStructure amounts.

Triggers:
  1. Employee created or salary changed → sync all structures for that employee
  2. SalaryComponent default_value or is_basic_salary changed → sync all employees
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='organization.Employee')
def on_employee_saved(sender, instance, created, **kwargs):
    """
    When a new employee is created or their CTC changes,
    auto-create/update all salary structure rows.
    """
    from apps.payroll.services.salary_structure_service import SalaryStructureService

    if created:
        logger.info(f"New employee detected — syncing salary structures | Employee: {instance.employee_id}")
        SalaryStructureService.sync_employee_structures(instance)
        return

    # Check if salary (CTC) changed — use update_fields if available
    update_fields = kwargs.get('update_fields')
    if update_fields and 'salary' not in update_fields:
        return  # salary didn't change, skip

    # If update_fields is None (full save), we can't be sure what changed,
    # so we re-sync to be safe. The service skips rows where amount is unchanged.
    logger.info(f"Employee salary may have changed — syncing structures | Employee: {instance.employee_id}")
    SalaryStructureService.sync_employee_structures(instance)


@receiver(post_save, sender='payroll.SalaryComponent')
def on_salary_component_saved(sender, instance, created, **kwargs):
    """
    When a SalaryComponent's default_value or is_basic_salary changes,
    recalculate structures for all employees.
    """
    from apps.payroll.services.salary_structure_service import SalaryStructureService

    if created:
        # New component — create structures for all existing employees
        logger.info(f"New salary component detected — syncing all employees | Component: {instance.code}")
        SalaryStructureService.sync_component_structures(instance)
        return

    # On update, re-sync. The service skips rows where amount is unchanged.
    update_fields = kwargs.get('update_fields')
    if update_fields:
        relevant = {'default_value', 'is_basic_salary'}
        if not relevant.intersection(update_fields):
            return  # irrelevant field update, skip

    logger.info(f"Salary component updated — syncing all employees | Component: {instance.code}")
    SalaryStructureService.sync_component_structures(instance)
