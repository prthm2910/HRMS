from django.contrib import admin
from apps.organization.models import Employee, Department, HOD
# Register your models here.

# admin.site.register(Employee)
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('department_id', 'name', 'description', 'created_at')
    search_fields = ('name',)

@admin.register(HOD)
class HODAdmin(admin.ModelAdmin):
    list_display = ('hod_id','employee', 'department', 'created_at')
    search_fields = ('employee__user__username', 'department__name')

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_id','user', 'department', 'designation', 'employment_type', 'joined_at')