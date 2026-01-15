from django.contrib import admin
from apps.base.utils import get_employee_profile
from apps.leaves.models import LeaveRequest, LeaveBalance


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    """
    Custom admin for LeaveRequest to handle action_by field automatically.
    """
    list_display = ['employee', 'leave_type', 'start_date', 'end_date', 'status', 'action_by', 'created_at']
    list_filter = ['status', 'leave_type', 'is_half_day', 'created_at']
    search_fields = ['employee__user__email', 'employee__employee_id', 'reason']
    readonly_fields = ['action_by', 'created_at', 'updated_at', 'duration']
    
    fieldsets = (
        ('Leave Details', {
            'fields': ('employee', 'leave_type', 'start_date', 'end_date', 'reason')
        }),
        ('Half-Day Options', {
            'fields': ('is_half_day', 'half_day_period'),
            'classes': ('collapse',)
        }),
        ('Status & Approval', {
            'fields': ('status', 'action_by', 'rejection_reason')
        }),
        ('Metadata', {
            'fields': ('duration', 'created_at', 'updated_at', 'is_active', 'is_deleted'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """
        Automatically set action_by when status changes to APPROVED or REJECTED.
        Only works if the admin user has an employee profile.
        """
        if change:  # Only for updates, not new records
            # Check if status field was changed
            if 'status' in form.changed_data:
                new_status = obj.status
                
                # If status is APPROVED or REJECTED, set action_by to current user's employee profile
                if new_status in ['APPROVED', 'REJECTED']:
                    admin_employee = get_employee_profile(request.user)
                    
                    if admin_employee:
                        obj.action_by = admin_employee
                    else:
                        # Admin doesn't have employee profile - show warning
                        from django.contrib import messages
                        messages.warning(
                            request,
                            f"Note: Your admin account ({request.user.email}) is not linked to an Employee profile. "
                            f"The 'Action By' field will be empty. Please create an Employee record for this admin user."
                        )
        
        super().save_model(request, obj, form, change)


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    """
    Custom admin for LeaveBalance with better display and filtering.
    """
    list_display = ['employee', 'leave_type', 'total_allocated', 'used_leaves', 'remaining_leaves']
    list_filter = ['leave_type']
    search_fields = ['employee__user__email', 'employee__employee_id']
    readonly_fields = ['remaining_leaves', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Employee & Leave Type', {
            'fields': ('employee', 'leave_type')
        }),
        ('Balance Details', {
            'fields': ('total_allocated', 'used_leaves', 'remaining_leaves')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'is_active', 'is_deleted'),
            'classes': ('collapse',)
        }),
    )
