from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.organization.views import EmployeeViewSet, DepartmentViewSet

# Single unified router
router = DefaultRouter()
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'departments', DepartmentViewSet, basename='department')

urlpatterns = [
    path('', include(router.urls)),
]