# hrms/apps/users/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.base.models import BaseTemplateModel

# ------------------------------------------------------------------
# CONCEPT: Custom User Model
# ------------------------------------------------------------------
class User(AbstractUser, BaseTemplateModel):
    # Inheritance:
    # - AbstractUser: Gives us username, password, groups, permissions (Django standard).
    # - BaseTemplateModel: Gives us UUID, created_at, is_deleted (Our custom rules).

    # Customization:
    # Django's default 'email' field is optional. We override it to be Unique & Required.
    email = models.EmailField(unique=True)
    
    # Extra fields not in default Django User
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.username # String representation (e.g., when printed in shell)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        db_table = 'users'  # Renames table from 'auth_user' (default) to 'users' (cleaner)