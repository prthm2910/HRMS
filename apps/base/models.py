from django.db import models
import uuid

# ==============================================================================
# BASE ARCHITECTURE MODELS
# ==============================================================================

class BaseTemplateModel(models.Model):
    """
    1. FIRST PRINCIPLES: The "Universal Blueprint"
    Think of 'BaseTemplateModel' as the DNA or the universal blueprint for 
    every record in your HRMS (Employees, Departments, Leaves). Instead of 
    re-inventing the wheel for every table, we define the "commonalities" 
    here once and let everyone else inherit them.

    2. TECHNICAL BREAKDOWN:
    - id (UUID): A globally unique identifier. Unlike simple numbers (1, 2, 3), 
      UUIDs are impossible to guess, which stops "Enumeration Attacks."
    - Audit Fields: 'created_at' (the birth certificate) and 'updated_at' 
      (the last modification log) update themselves automatically.
    - Soft Delete: We use 'is_deleted' instead of actual deletion. This 
      keeps historical data safe in the database but hides it from the user.
    - abstract = True: Tells Django not to create a database table for this. 
      It only exists to be a parent for other models.
    """
    
    # 1. Unique Identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 2. Automatic Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 3. Activation & Soft Delete
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True