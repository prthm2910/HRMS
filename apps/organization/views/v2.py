from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from organization.models import Employee, Department
from organization.serializers import EmployeeSerializer, DepartmentSerializer

@extend_schema(tags=['V2 - Departments (Soft Delete)'])
class DepartmentViewSetV2(viewsets.ModelViewSet):
    """
    V2: Department Soft Delete.
    Access: Anyone authenticated can View. Only Admins can Create/Update/Delete.
    """
    queryset = Department.objects.filter(is_deleted=False).order_by('name')
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.is_active = False
        instance.save()

@extend_schema(tags=['V2 - Employees (Soft Delete)'])
class EmployeeViewSetV2(viewsets.ModelViewSet):
    """
    V2: Employee Soft Delete.
    Access:
    - Admin: Full Access.
    - Manager: View Self + Team subordinates.
    - Employee: View Self only.
    - Write Operations: Admin only.
    """
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        # 1. Admin/Staff bypass - Check this FIRST
        if user.is_superuser or user.is_staff:
            return Employee.objects.filter(is_deleted=False).order_by('-created_at')
        
        # 2. Get profile for regular users
        employee_profile = getattr(user, 'employee_profile', None)
        
        # 3. If no profile and not Admin, return nothing
        if not employee_profile:
            return Employee.objects.none()

        # 4. Ownership & Management Filter
        return Employee.objects.filter(
            Q(id=employee_profile.id) | Q(manager=employee_profile),
            is_deleted=False
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
                {"detail": "Forbidden: Employee records can only be deactivated by Admins."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    def perform_destroy(self, instance):
        # Soft Delete Logic
        instance.is_deleted = True
        instance.is_active = False
        instance.save()
        # Deactivate the associated Auth User
        if instance.user:
            instance.user.is_active = False
            instance.user.save()