from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    # 1. 'action' is now FIRST in the list
    list_display = ('action', 'timestamp', 'actor', 'table_name', 'request_source_display')
    
    # 2. This makes the 'action' column the clickable link to view details
    list_display_links = ('action',)

    # 3. Filters for the right sidebar
    list_filter = ('action', 'table_name', 'timestamp')
    
    # 4. Search bar
    search_fields = ('record_id', 'actor__email', 'changes', 'path')

    # 5. Make everything Read-Only
    readonly_fields = [field.name for field in AuditLog._meta.fields]

    # --- CUSTOM COLUMN DISPLAY ---
    def request_source_display(self, obj):
        return obj.request_source
    
    request_source_display.short_description = "Source"

    # --- SECURITY PERMISSIONS ---
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False