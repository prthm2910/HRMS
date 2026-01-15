from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.forms.models import model_to_dict
from django.contrib.auth import get_user_model
import json

from apps.audit.models import AuditLog
from apps.base.utils import get_audit_data

# 1. Get the User Model dynamically
User = get_user_model()
UserModelName = User.__name__

# 2. Add User Model to the list
TRACKED_MODELS = ['Employee', 'LeaveRequest', 'Department', 'LeaveBalance', UserModelName]

# 3. Define Sensitive Fields to Hide (Security Best Practice)
SENSITIVE_FIELDS = ['password', 'is_superuser', 'is_staff', 'groups', 'user_permissions']

def sanitize_changes(changes):
    """
    Removes sensitive keys like 'password' from the changes log.
    """
    if not changes:
        return {}
    
    # If it's a "create" or "delete" (full dict)
    if not any(isinstance(v, dict) for v in changes.values()):
        for field in SENSITIVE_FIELDS:
            if field in changes:
                changes[field] = "********"
    
    # If it's an "update" (nested dict: {'password': {'old': '...', 'new': '...'}})
    else:
        for field in SENSITIVE_FIELDS:
            if field in changes:
                changes[field] = {"old": "********", "new": "********"}
                
    return changes

@receiver(pre_save)
def capture_old_state(sender, instance, **kwargs):
    if sender.__name__ not in TRACKED_MODELS:
        return
    
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            instance._old_state = model_to_dict(old_instance)
        except sender.DoesNotExist:
            instance._old_state = None
    else:
        instance._old_state = None

@receiver(post_save)
def log_create_or_update(sender, instance, created, **kwargs):
    if sender.__name__ not in TRACKED_MODELS:
        return

    data = get_audit_data()
    actor = data.get('user')
    user_agent = data.get('user_agent')
    path = data.get('path')

    new_state = model_to_dict(instance)
    changes = {}
    action = 'UPDATE'

    if created:
        action = 'CREATE'
        changes = json.loads(json.dumps(new_state, default=str))
    else:
        old_state = getattr(instance, '_old_state', {})
        
        if old_state:
            for key, new_value in new_state.items():
                old_value = old_state.get(key)
                if old_value != new_value:
                    changes[key] = {
                        "old": str(old_value) if old_value is not None else None,
                        "new": str(new_value) if new_value is not None else None
                    }

        # Check for Soft Delete
        if 'is_deleted' in changes and getattr(instance, 'is_deleted', False) is True:
            action = 'DELETE'
    
    # 4. SANITIZE BEFORE SAVING (Hide Passwords)
    changes = sanitize_changes(changes)

    if changes or created:
        AuditLog.objects.create(
            actor=actor, 
            action=action,
            table_name=sender.__name__,
            record_id=str(instance.pk),
            changes=changes,
            user_agent=user_agent,
            path=path
        )

@receiver(post_delete)
def log_hard_delete(sender, instance, **kwargs):
    if sender.__name__ not in TRACKED_MODELS:
        return

    data = get_audit_data()
    
    changes = model_to_dict(instance)
    changes = json.loads(json.dumps(changes, default=str))
    
    # Sanitize Delete Logs too
    changes = sanitize_changes(changes)

    AuditLog.objects.create(
        actor=data.get('user'),
        action='HARD_DELETE',
        table_name=sender.__name__,
        record_id=str(instance.pk),
        changes=changes,
        user_agent=data.get('user_agent'),
        path=data.get('path')
    )