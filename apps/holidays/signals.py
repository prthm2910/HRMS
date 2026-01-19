from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from datetime import date
from apps.holidays.models import Holiday


@receiver(post_save, sender=Holiday)
def recalculate_leaves_on_holiday_create(sender, instance, created, **kwargs):
    """
    When a new holiday is created, recalculate affected leave requests.
    Only affects PENDING and APPROVED leaves with start_date >= today.
    """
    # Only recalculate for active holidays
    if not instance.is_active or instance.is_deleted:
        return
    
    # Only recalculate for newly created holidays or when reactivating
    if created or kwargs.get('update_fields') and 'is_active' in kwargs.get('update_fields', []):
        _recalculate_affected_leaves(instance.date, instance.region)


@receiver(post_delete, sender=Holiday)
def recalculate_leaves_on_holiday_delete(sender, instance, **kwargs):
    """
    When a holiday is deleted, recalculate affected leave requests.
    This may increase leave duration for affected requests.
    """
    _recalculate_affected_leaves(instance.date, instance.region)


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
    from apps.base.utils import calculate_working_days
    
    # Find affected leave requests
    affected_leaves = LeaveRequest.objects.filter(
        status__in=['PENDING', 'APPROVED'],
        start_date__lte=holiday_date,
        end_date__gte=holiday_date,
        start_date__gte=date.today(),  # Only future leaves
        is_deleted=False
    )
    
    print("\n" + "="*70)
    print(f"🔄 LEAVE RECALCULATION TRIGGERED")
    print("="*70)
    print(f"Holiday Date: {holiday_date}")
    print(f"Region: {region or 'All'}")
    print(f"Affected Leaves: {affected_leaves.count()}")
    print("="*70)
    
    for leave in affected_leaves:
        # Calculate old duration
        old_duration = leave.duration
        
        # Recalculate new duration
        new_duration, excluded_holidays = calculate_working_days(
            leave.start_date,
            leave.end_date,
            region=region
        )
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
                
                print(f"\n✅ Updated Leave Request ID: {leave.id}")
                print(f"   Employee: {leave.employee.employee_id}")
                print(f"   Period: {leave.start_date} to {leave.end_date}")
                print(f"   Old Duration: {old_duration} days")
                print(f"   New Duration: {new_duration} days")
                print(f"   Credited Back: {duration_diff} days")
                print(f"   New Balance: {balance.remaining_leaves} {leave.leave_type} leaves")
                
            except LeaveBalance.DoesNotExist:
                print(f"\n⚠️  Warning: No balance record found for {leave.employee.employee_id}")
    
    print("="*70 + "\n")
