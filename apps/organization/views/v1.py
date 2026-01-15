from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from apps.base.utils import get_employee_profile
from apps.organization.models import Employee, Department
from apps.organization.serializers import EmployeeSerializer, DepartmentSerializer

@extend_schema(tags=['V1 - Departments (Hard Delete)'])
class DepartmentViewSetV1(viewsets.ModelViewSet):
    """
    V1: Department Hard Delete.
    Access: Anyone authenticated can View. Only Admins can Create/Update/Delete.
    """
    queryset = Department.objects.all().order_by('name')
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

@extend_schema(tags=['V1 - Employees (Hard Delete)'])
class EmployeeViewSetV1(viewsets.ModelViewSet):
    """
    V1: Employee Hard Delete.
    Access:
    - Admin: Full Access to all data.
    - Manager: View Self + Team subordinates.
    - Employee: View Self only.
    - Write Operations: Admin only (returns 403 otherwise).
    """
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        # 1. Admin/Staff bypass - Check this FIRST so Admin doesn't need a profile
        if user.is_superuser or user.is_staff:
            return Employee.objects.all().order_by('-created_at')
        
        # 2. Get profile for regular users
        employee_profile = get_employee_profile(user)
        
        # 3. If no profile and not Admin, return nothing
        if not employee_profile:
            return Employee.objects.none()

        # 4. Filter for Managers (Self + Team) and Employees (Self Only)
        return Employee.objects.filter(
            Q(id=employee_profile.id) | Q(manager=employee_profile)
        ).distinct().order_by('-created_at')

    def create(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return Response(
                {"detail": "Forbidden: Only Administrators can onboard new employees."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return Response(
                {"detail": "Forbidden: Only Administrators can modify employee records."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return Response(
                {"detail": "Forbidden: Only Administrators can permanently delete employee records."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)