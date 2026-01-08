from django.db import models
import uuid
# Create your models here.
# ------------------------------------------------------------------
# CONCEPT: Abstract Base Classes (Don't Repeat Yourself)
# ------------------------------------------------------------------
class BaseTemplateModel(models.Model):
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

    # 3. Soft Delete Pattern
    # Instead of actually deleting data (SQL DELETE), we just hide it (is_deleted=True).
    # This is critical for HR systems to maintain historical records.
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True # CRITICAL: This tells Django "Don't make a table for this class".
                        # Only make tables for models that INHERIT from this.