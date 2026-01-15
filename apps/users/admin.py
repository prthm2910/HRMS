# hrms/apps/users/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from apps.users.models import User

class CustomUserAdmin(UserAdmin):
    model = User
    
    # 1. List View Customization
    # Controls columns in the user list table.
    # Added 'phone_number' which isn't there by default.
    list_display = ['username', 'email', 'phone_number', 'is_staff']

    # 2. Edit Page Customization (Fieldsets)
    # Django's default UserAdmin doesn't know about 'bio' or 'phone_number'.
    # We append a new section "Additional Info" to the existing form.
    fieldsets = list(UserAdmin.fieldsets) + [
        ('Additional Info', {'fields': ('phone_number', 'bio')}),
    ]

    # 3. Add Page Customization
    # When creating a NEW user, we also want to see these fields.
    add_fieldsets = list(UserAdmin.add_fieldsets) + [
        ('Additional Info', {'fields': ('phone_number', 'bio')}),
    ]

admin.site.register(User, CustomUserAdmin)