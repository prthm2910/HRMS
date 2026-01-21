from django.contrib import admin
from apps.audit.models import AuditLog, AIOperationLog


class AIOperationInline(admin.StackedInline):
    """Inline display of AI operation details within AuditLog admin"""
    model = AIOperationLog
    extra = 0
    can_delete = False
    readonly_fields = [
        'operation_type', 'model_used', 'input_data', 'output_data',
        'status', 'processing_time_seconds', 'error_message', 'created_at'
    ]
    fields = [
        'operation_type', 'model_used', 'status', 'processing_time_seconds',
        'input_data', 'output_data', 'error_message', 'created_at'
    ]


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
    
    # Show AI operation details inline when action is AI_SERVICE
    def get_inlines(self, request, obj=None):
        if obj and obj.action == 'AI_SERVICE':
            return [AIOperationInline]
        return []

    # --- SECURITY PERMISSIONS ---
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AIOperationLog)
class AIOperationLogAdmin(admin.ModelAdmin):
    """Admin interface for AI Operation Logs"""
    list_display = [
        'created_at', 'operation_type', 'status', 'model_used', 
        'processing_time_seconds', 'get_user'
    ]
    list_filter = ['operation_type', 'status', 'created_at', 'model_used']
    search_fields = ['audit_log__actor__email', 'audit_log__actor__username', 'error_message']
    readonly_fields = [
        'audit_log', 'operation_type', 'model_used', 'input_data', 
        'output_data', 'status', 'processing_time_seconds', 'error_message', 'created_at'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    def get_user(self, obj):
        """Get the user who initiated the AI operation"""
        if obj.audit_log and obj.audit_log.actor:
            return obj.audit_log.actor.email
        return "System/Unknown"
    get_user.short_description = 'User'
    
    fieldsets = (
        ('Operation Info', {
            'fields': ('audit_log', 'operation_type', 'model_used', 'status', 'processing_time_seconds')
        }),
        ('Input/Output Data', {
            'fields': ('input_data', 'output_data'),
            'classes': ('collapse',)
        }),
        ('Error Details', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )
    
    def has_add_permission(self, request):
        """Prevent manual creation of AI operation logs"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of AI operation logs"""
        return False