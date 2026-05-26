from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from datetime import date
from apps.holidays.models import Holiday
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Holiday)
def recalculate_leaves_on_holiday_create(sender, instance, created, **kwargs):
    """
    When a new holiday is created, recalculate affected leave requests.
    Only affects PENDING and APPROVED leaves with start_date >= today.
    """
    # Only recalculate for active holidays
    if not instance.is_active or instance.is_deleted:
        logger.debug(f"Skipping recalculation for inactive/deleted holiday: {instance.holiday_date}")
        return
    
    # Only recalculate for newly created holidays or when reactivating
    if created or kwargs.get('update_fields') and 'is_active' in kwargs.get('update_fields', []):
        logger.info(f"Holiday created/reactivated: {instance.holiday_date} (Region: {instance.region or 'All'})")
        _recalculate_affected_leaves(instance.holiday_date.date(), instance.region)


@receiver(post_delete, sender=Holiday)
def recalculate_leaves_on_holiday_delete(sender, instance, **kwargs):
    """
    When a holiday is deleted, recalculate affected leave requests.
    This may increase leave duration for affected requests.
    """
    logger.info(f"Holiday deleted: {instance.holiday_date} (Region: {instance.region or 'All'})")
    _recalculate_affected_leaves(instance.holiday_date.date(), instance.region)


def _recalculate_affected_leaves(holiday_date, region=None):
    """
    Recalculate leave durations for future approved/pending leaves
    that overlap with the holiday date.
    
    Strategy (Option A):
    - Only affects PENDING and APPROVED leaves
    - Only affects leaves where start_date >= today
    - Adjusts leave balances (credits back days)
    - Logs changes in terminal
    """
    from apps.leaves.models import LeaveRequest, LeaveBalance
    from apps.base.utils import calculate_working_and_non_working_days
    
    # Find affected leave requests
    affected_leaves = LeaveRequest.objects.filter(
        status__in=['PENDING', 'APPROVED'],
        started_at__date__lte=holiday_date,
        ended_at__gte=holiday_date,
        started_at__date__gte=date.today(),  # Only future leaves
        is_deleted=False
    )
    
    logger.info(f"Recalculating leaves for holiday on {holiday_date} (Region: {region or 'All'}). Affected leaves: {affected_leaves.count()}")
    
    for leave in affected_leaves:
        # Calculate old duration
        old_duration = leave.duration
        
        # Recalculate new duration
        res = calculate_working_and_non_working_days(
            leave.started_at.date(),
            leave.ended_at.date(),
            region=region
        )
        new_duration = res['working_days']
        excluded_holidays = res['holidays']
        new_duration = float(new_duration)
        
        # If duration changed, update leave balance
        if old_duration != new_duration:
            duration_diff = old_duration - new_duration
            
            # Update leave balance (credit back the difference)
            try:
                balance = LeaveBalance.objects.get(
                    employee=leave.employee,
                    leave_type=leave.leave_type
                )
                balance.used_leaves -= duration_diff
                balance.save()
                
                logger.info(
                    f"Leave recalculated - ID: {leave.id}, Employee: {leave.employee.employee_id}, "
                    f"Period: {leave.started_at.date()} to {leave.ended_at.date()}, "
                    f"Old: {old_duration}d, New: {new_duration}d, Credited: {duration_diff}d"
                )
                
            except LeaveBalance.DoesNotExist:
                logger.warning(f"No balance record found for employee {leave.employee.employee_id} (Leave ID: {leave.id})")
    
