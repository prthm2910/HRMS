from django.contrib import admin
from apps.holidays.models import Holiday, HolidayUpload


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    """
    Admin interface for managing holidays.
    """
    list_display = [
        'date', 
        'name', 
        'region', 
        'is_recurring', 
        'is_active',
        'is_deleted',
        'created_at'
    ]
    
    list_filter = [
        'is_recurring',
        'is_active',
        'is_deleted',
        'region',
        'date'
    ]
    
    search_fields = [
        'name',
        'description',
        'region'
    ]
    
    readonly_fields = [
        'id',
        'recurring_group_id',
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('Holiday Information', {
            'fields': ('date', 'name', 'description', 'region')
        }),
        ('Recurring Settings', {
            'fields': ('is_recurring', 'recurring_group_id')
        }),
        ('Special Flags', {
            'fields': ('is_working_day', 'is_active', 'is_deleted')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['-date']
    date_hierarchy = 'date'
    
    def get_queryset(self, request):
        """Show all holidays including soft-deleted ones in admin"""
        qs = super().get_queryset(request)
        return qs  # Don't filter out deleted items in admin


@admin.register(HolidayUpload)
class HolidayUploadAdmin(admin.ModelAdmin):
    """
    Admin interface for viewing holiday upload history.
    """
    list_display = [
        'id',
        'uploaded_by',
        'extraction_status',
        'created_at',
        'image_preview'
    ]
    
    list_filter = [
        'extraction_status',
        'created_at'
    ]
    
    search_fields = [
        'uploaded_by__username',
        'uploaded_by__email',
        'error_message'
    ]
    
    readonly_fields = [
        'id',
        'uploaded_by',
        'image',
        'extracted_data',
        'extraction_status',
        'error_message',
        'created_at',
        'updated_at',
        'image_preview'
    ]
    
    fieldsets = (
        ('Upload Information', {
            'fields': ('uploaded_by', 'created_at', 'extraction_status')
        }),
        ('Image', {
            'fields': ('image', 'image_preview')
        }),
        ('Extraction Results', {
            'fields': ('extracted_data', 'error_message')
        }),
        ('Metadata', {
            'fields': ('id', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def image_preview(self, obj):
        """Display image preview in admin"""
        if obj.image:
            from django.utils.html import format_html
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 300px;" />',
                obj.image.url
            )
        return "No image"
    image_preview.short_description = "Image Preview"
    
    def has_add_permission(self, request):
        """Disable manual creation in admin (uploads only via API)"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion to clean up old uploads"""
        return True
