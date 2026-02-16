"""
Signal handlers for BaseModel to auto-populate created_by and updated_by fields.
Uses existing audit infrastructure (get_audit_data) to retrieve user from thread-local storage.
"""

from django.db.models.signals import pre_save
from django.dispatch import receiver
from apps.base.models import BaseModel
from apps.base.utils import get_audit_data


@receiver(pre_save)
def populate_audit_fields(sender, instance, **kwargs):
    """
    Auto-populate created_by and updated_by fields for all BaseModel instances.
    
    This signal runs before saving any model that inherits from BaseModel.
    It retrieves the current user from thread-local storage (set by AuditMiddleware)
    and populates the audit fields accordingly.
    
    Args:
        sender: The model class
        instance: The model instance being saved
        **kwargs: Additional keyword arguments
    """
    # Only process models that inherit from BaseModel
    if not isinstance(instance, BaseModel):
        return
    
    # Get audit data from thread-local storage
    audit_data = get_audit_data()
    user = audit_data.get('user')
    
    # Skip if no user in context (e.g., management commands, system operations)
    if not user:
        return
    
    # Set created_by only on creation (when pk is None)
    if instance.pk is None and not instance.created_by:
        instance.created_by = user
    
    # Always update updated_by
    instance.updated_by = user
