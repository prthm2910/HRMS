# hrms/apps/users/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.base.models import BaseModel

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

    # Customization:
    # Django's default 'email' field is optional. We override it to be Unique & Required.
    email = models.EmailField(unique=True)
    
    # Extra fields not in default Django User
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)

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