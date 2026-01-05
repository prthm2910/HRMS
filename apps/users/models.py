import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


# Create your models here.
class BaseTemplateModel(models.Model):
    # 1. Security: Use UUID instead of 1, 2, 3
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 2. Time Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 3. Soft Delete & Status
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True # This model won't create its own table
        
class User(AbstractUser, BaseTemplateModel):
    # Making email unique and required (Django default is optional)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        db_table = 'users'  # Custom table name in the database



