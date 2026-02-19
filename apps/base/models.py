from django.db import models
from django.conf import settings
import uuid
# Create your models here.
# ------------------------------------------------------------------
# CONCEPT: Abstract Base Classes (Don't Repeat Yourself)
# ------------------------------------------------------------------
class BaseModel(models.Model):
    """
    A foundational model that provides common fields for ALL other models.
    """
    
    # 1. Security & Scalability: UUID
    # Why? Unlike integers (1, 2, 3), UUIDs (e.g., a1b2-c3d4...) are hard to guess.
    # This prevents "ID Enumeration Attacks" where a hacker guesses /users/5, /users/6.
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 2. Audit Trails (Time Tracking)
    # auto_now_add=True: Sets the time ONLY when created.
    # auto_now=True: Updates the time EVERY time you save.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 3. Audit Trails (User Tracking)
    # Tracks which user created/updated the record
    # null=True, blank=True allows system operations without authenticated user
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_%(class)s_set',
        help_text='User who created this record'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_%(class)s_set',
        help_text='User who last updated this record'
    )

    # 4. Soft Delete Pattern
    # Instead of actually deleting data (SQL DELETE), we just hide it (is_deleted=True).
    # This is critical for HR systems to maintain historical records.
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        """
        Overridden save method to handle:
        1. Automated Human-Readable ID (HRID) generation.
        """
        # Look for HRID configuration attributes in child classes
        prefix = getattr(self, '_display_id_prefix', None)
        field_name = getattr(self, '_display_id_field', None)
        
        if prefix and field_name:
            # Only generate if the field is currently empty
            if not getattr(self, field_name, None):
                from apps.base.utils import generate_unique_id
                
                new_id = generate_unique_id(
                    model_class=self.__class__, 
                    field_name=field_name, 
                    prefix=prefix, 
                    length=6
                )
                setattr(self, field_name, new_id)
        
        super().save(*args, **kwargs)

    class Meta:
        abstract = True # CRITICAL: This tells Django "Don't make a table for this class".
                        # Only make tables for models that INHERIT from this.
