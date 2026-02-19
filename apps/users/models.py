# hrms/apps/users/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.base.models import BaseModel
from phonenumber_field.modelfields import PhoneNumberField
import logging

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# CONCEPT: Custom User Model
# ------------------------------------------------------------------
class User(AbstractUser, BaseModel):
    """
    Custom User Model combining Django's built-in auth with our custom fields.
    - AbstractUser: Gives us username, password, email, etc. (Django's built-in).
    - BaseModel: Gives us UUID, created_at, is_deleted (Our custom rules).
    """

    user_id = models.CharField(
        max_length=20, 
        unique=True, 
        editable=False,
        null=True,
        help_text="Format: USRXXXXXX"
    )

    _display_id_prefix = 'USR'
    _display_id_field = 'user_id'

    # Customization:
    # Django's default 'email' field is optional. We override it to be Unique & Required.
    email = models.EmailField(unique=True)
    
    # Extra fields not in default Django User
    phone_number = PhoneNumberField(blank=True, null=True, help_text="Enter number with country code (e.g., +919876543210)")
    bio = models.TextField(blank=True, null=True)

    @property
    def phone_country_code(self):
        """Returns the country code (e.g., '+91')"""
        if self.phone_number:
            return f"+{self.phone_number.country_code}"
        return None

    @property
    def phone_national_number(self):
        """Returns the national number (e.g., '9876543210')"""
        if self.phone_number:
            return str(self.phone_number.national_number)
        return None

    @property
    def phone_full(self):
        """Returns the full E.164 formatted number"""
        return str(self.phone_number) if self.phone_number else None

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        # Track status change
        old_active = None
        if not is_new:
            try:
                old_active = User.objects.get(pk=self.pk).is_active
            except User.DoesNotExist:
                pass

        super().save(*args, **kwargs)
        
        if is_new:
            logger.info(f"New user account created | User ID: {self.id} | Username: {self.username} | Status: {'Active' if self.is_active else 'Inactive'}")
        elif old_active is not None and old_active != self.is_active:
            status_text = "Activated" if self.is_active else "Deactivated"
            logger.info(f"User account status changed | User ID: {self.id} | New Status: {status_text}")

    def __str__(self):
        return self.username # String representation (e.g., when printed in shell)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        db_table = 'users'  # Renames table from 'auth_user' (default) to 'users' (cleaner)