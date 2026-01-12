from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from organization.models import Employee
from .models import LeaveBalance, LeaveRequest
from django.db.models import F

# --- 1. Auto-Create Balances for New Employees ---
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
        LeaveBalance.objects.bulk_create(balances)

# --- 2. Capture Previous Status (The Memory) ---
@receiver(pre_save, sender=LeaveRequest)
def capture_previous_status(sender, instance, **kwargs):
    """
    Before saving, store the old status to compare later.
    """
    print(f"🔍 PRE_SAVE signal fired for LeaveRequest ID: {instance.pk}")
    if instance.pk:
        try:
            old_record = LeaveRequest.objects.get(pk=instance.pk)
            instance._old_status = old_record.status
            print(f"   Old status captured: {old_record.status}")
        except LeaveRequest.DoesNotExist:
            instance._old_status = None
            print(f"   LeaveRequest not found in DB (shouldn't happen)")
    else:
        instance._old_status = None
        print(f"   New LeaveRequest being created (no old status)")

# --- 3. The Smart Ledger Logic (Deduct & Refund) ---
@receiver(post_save, sender=LeaveRequest)
def update_leave_balance_on_status_change(sender, instance, created, **kwargs):
    """
    Handles both DEDUCTION (when Approved) and REFUND (when Revoked).
    """
    print(f"🔍 POST_SAVE signal fired for LeaveRequest ID: {instance.pk}, Created: {created}")
    
    if created:
        print(f"   Skipping: New leave request created")
        return

    # Get the old status we captured in pre_save
    old_status = getattr(instance, '_old_status', None)
    new_status = instance.status
    
    print(f"   Old status: {old_status}, New status: {new_status}")

    # If status hasn't changed, do nothing
    if old_status == new_status:
        print(f"   Skipping: Status hasn't changed")
        return

    # Calculate days
    days_diff = instance.duration

    try:
        balance = LeaveBalance.objects.get(
            employee=instance.employee, 
            leave_type=instance.leave_type
        )
        
        # SCENARIO A: Granting Leave (Pending -> Approved)
        # Action: INCREASE used_leaves (Deduct Balance)
        if new_status == 'APPROVED' and old_status != 'APPROVED':
            print(f"📉 Deducting {days_diff} days for {instance.employee}")
            balance.used_leaves = F('used_leaves') + days_diff
            balance.save()

        # SCENARIO B: Revoking Leave (Approved -> Rejected / Cancelled)
        # Action: DECREASE used_leaves (Refund Balance)
        elif old_status == 'APPROVED' and new_status != 'APPROVED':
            print(f"📈 Refunding {days_diff} days to {instance.employee}")
            # We use F() to handle potential race conditions safely
            balance.used_leaves = F('used_leaves') - days_diff
            balance.save()
            
    except LeaveBalance.DoesNotExist:
        print(f"⚠️ CRITICAL: No Leave Balance found for {instance.employee}")