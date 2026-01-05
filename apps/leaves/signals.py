from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from organization.models import Employee
from .models import LeaveBalance, LeaveRequest
from django.db.models import F

# --- 1. Trigger on New Employee (This part was already correct) ---
@receiver(post_save, sender=Employee)
def create_leave_balances(sender, instance, created, **kwargs):
    if created:
        defaults = {
            'SICK': 10,
            'CASUAL': 12,
            'EARNED': 15,
            'UNPAID': 0
        }

        balances = []
        for code, label in LeaveRequest.LEAVE_TYPE_CHOICES:
            balances.append(
                LeaveBalance(
                    employee=instance,
                    leave_type=code,
                    total_allocated=defaults.get(code, 0),
                    used_leaves=0
                )
            )
        
        # Bulk create is faster than looping .create()
        LeaveBalance.objects.bulk_create(balances)

# --- 2. Fix for "Double Deduction" Bug ---

@receiver(pre_save, sender=LeaveRequest)
def capture_previous_status(sender, instance, **kwargs):
    """
    Before saving, we check what the status currently is in the DB.
    We store it in a temporary variable '_old_status'.
    """
    if instance.pk:
        try:
            old_record = LeaveRequest.objects.get(pk=instance.pk)
            instance._old_status = old_record.status
        except LeaveRequest.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=LeaveRequest)
def update_leave_balance_on_approval(sender, instance, created, **kwargs):
    """
    Only deduct balance if status TRANSITIONS from 'PENDING' -> 'APPROVED'.
    """
    if created:
        return

    # Get the old status we captured in pre_save
    old_status = getattr(instance, '_old_status', None)

    # CHECK: Is it Approved NOW? AND Was it NOT Approved BEFORE?
    if instance.status == 'APPROVED' and old_status != 'APPROVED':
        
        days_to_deduct = instance.duration
        
        try:
            balance = LeaveBalance.objects.get(
                employee=instance.employee, 
                leave_type=instance.leave_type
            )
            
            # Atomic Update (Safe against race conditions)
            balance.used_leaves = F('used_leaves') + days_to_deduct
            balance.save()
            
            # Refresh to show updated number in logs/print if needed
            balance.refresh_from_db()
            print(f"✅ Deducted {days_to_deduct} days. New Used: {balance.used_leaves}")

        except LeaveBalance.DoesNotExist:
            print(f"⚠️ CRITICAL: No Leave Balance found for {instance.employee.email}")