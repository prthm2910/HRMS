from django.contrib import admin
from apps.organization.models import Employee, Department
# Register your models here.

admin.site.register(Employee)
admin.site.register(Department)