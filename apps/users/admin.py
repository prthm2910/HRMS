from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    model = User
    
    # 1. Display these fields in the list view (the table of all users)
    list_display = ['username', 'email', 'phone_number', 'is_staff']

    # 2. Add your custom fields to the "Edit User" page
    # We append a new section called 'Additional Info' to the existing fieldsets
    fieldsets = list(UserAdmin.fieldsets) + [
        ('Additional Info', {'fields': ('phone_number', 'bio')}),
    ]

    # 3. Add your custom fields to the "Add User" page
    # This controls what you see when you click "Add User" in the admin
    add_fieldsets = list(UserAdmin.add_fieldsets) + [
        ('Additional Info', {'fields': ('phone_number', 'bio')}),
    ]

admin.site.register(User, CustomUserAdmin)