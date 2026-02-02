from django.contrib import admin
from apps.organization.models import Employee, Department, HOD
# Register your models here.

# admin.site.register(Employee)
admin.site.register(Department)

@admin.register(HOD)
class HODAdmin(admin.ModelAdmin):
    list_display = ('employee', 'department', 'created_at')
    search_fields = ('employee__user__username', 'department__name')

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('user', 'employee_id', 'department', 'designation', 'employment_type', 'date_of_joining')