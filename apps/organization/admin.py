from django.contrib import admin
from apps.organization.models import Employee, Department
# Register your models here.

# admin.site.register(Employee)
admin.site.register(Department)

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('user', 'employee_id', 'department', 'designation', 'employment_type', 'date_of_joining')