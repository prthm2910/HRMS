from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Import from the new package structure
from apps.organization.views.v1 import EmployeeViewSetV1, DepartmentViewSetV1
from apps.organization.views.v2 import EmployeeViewSetV2, DepartmentViewSetV2

# --- V1 Router (Hard Delete) ---
router_v1 = DefaultRouter()
router_v1.register(r'employees', EmployeeViewSetV1, basename='employee-v1')
router_v1.register(r'departments', DepartmentViewSetV1, basename='department-v1')

# --- V2 Router (Soft Delete) ---
router_v2 = DefaultRouter()
router_v2.register(r'employees', EmployeeViewSetV2, basename='employee-v2')
router_v2.register(r'departments', DepartmentViewSetV2, basename='department-v2')

urlpatterns = [
    # V1: http://localhost:8000/api/employees/v1/employees/
    path('v1/', include(router_v1.urls)),

    # V2: http://localhost:8000/api/employees/v2/employees/
    path('v2/', include(router_v2.urls)),
]