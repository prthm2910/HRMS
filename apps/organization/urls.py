from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Import from standard views.py
from apps.organization.views import (
    EmployeeSoftDeleteViewSet,
    DepartmentSoftDeleteViewSet,
    EmployeeHardDeleteViewSet,
    DepartmentHardDeleteViewSet
)

# --- Soft Delete Router (Default) ---
router_soft = DefaultRouter()
router_soft.register(r'employees', EmployeeSoftDeleteViewSet, basename='employee-soft')
router_soft.register(r'departments', DepartmentSoftDeleteViewSet, basename='department-soft')

# --- Hard Delete Router ---
router_hard = DefaultRouter()
router_hard.register(r'employees', EmployeeHardDeleteViewSet, basename='employee-hard')
router_hard.register(r'departments', DepartmentHardDeleteViewSet, basename='department-hard')

urlpatterns = [
    # Soft Delete (Default): /api/organization/employees/, /api/organization/departments/
    path('', include(router_soft.urls)),

    # Hard Delete: /api/organization/employees/hard/, /api/organization/departments/hard/
    path('hard/', include(router_hard.urls)),
]