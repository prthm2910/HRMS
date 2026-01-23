from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.base.models import BaseTemplateModel

# ==============================================================================
# CUSTOM USER IDENTITY MODEL
# ==============================================================================

class User(AbstractUser, BaseTemplateModel):
    """
    1. FIRST PRINCIPLES: The "Custom Badge System"
    Every person on the system needs a digital badge. Django provides a 
    standard badge (AbstractUser) with basics like 'username' and 'password'. 
    However, for a professional HRMS, we want to stamp our own "Custom Seal" 
    on it (BaseTemplateModel) to add UUIDs and security timestamps.

    2. TECHNICAL BREAKDOWN:
    - AbstractUser: We inherit from this so we don't have to code 'login' 
      and 'logout' from scratch. It handles password hashing and security.
    - BaseTemplateModel: Adds our custom project-wide fields like 'id' (UUID) 
      and 'created_at'.
    - email: We explicitly set unique=True. This means two people cannot 
      register with the same email, keeping the filing system accurate.
    - phone_number & bio: Extra storage for personal details not found in 
      standard Django.
    """
    
    # Override email to be unique and required
    email = models.EmailField(unique=True)
    
    # Personal Extra Details
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.username # String representation (e.g., when printed in shell)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        db_table = 'users'  # Renames table from 'auth_user' (default) to 'users' (cleaner)