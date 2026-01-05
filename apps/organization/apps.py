from django.apps import AppConfig

class OrganizationConfig(AppConfig):  # Renamed from EmployeesConfig
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'organization'             # Renamed from 'employees'