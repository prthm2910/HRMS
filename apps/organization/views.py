from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from apps.base.utils import get_employee_profile
from apps.base.views import (
    BaseAuthenticatedViewSet, 
    BaseReadAuthWriteAdminViewSet, 
    SoftDeleteMixin, 
    AdminWritePermissionMixin,
    BaseRoleFilteredViewSet
)
from apps.organization.models import Employee, Department
from apps.organization.serializers import EmployeeSerializer, DepartmentSerializer


# ============================================================================
# SOFT DELETE VIEWSETS (Default - Recommended)
# ============================================================================

@extend_schema(tags=['Departments (Soft Delete)'])
class DepartmentSoftDeleteViewSet(SoftDeleteMixin, BaseReadAuthWriteAdminViewSet):
    """
    Department Soft Delete.
    Access: Anyone authenticated can View. Only Admins can Create/Update/Delete.
    Delete operation marks records as deleted without removing from database.
    """
    queryset = Department.objects.filter(is_deleted=False).order_by('name')
    serializer_class = DepartmentSerializer


@extend_schema(tags=['Employees (Soft Delete)'])
class EmployeeSoftDeleteViewSet(AdminWritePermissionMixin, SoftDeleteMixin, BaseRoleFilteredViewSet):
    """
    Employee Soft Delete.
    Access:
    - Admin: Full Access.
    - Manager: View Self + Team subordinates.
    - Employee: View Self only.
    - Write Operations: Admin only.
    Delete operation marks records as deleted without removing from database.
    """
    queryset = Employee.objects.filter(is_deleted=False)
    serializer_class = EmployeeSerializer
    admin_forbidden_message = "Forbidden: Only Administrators have permission to manage employee profiles."

    def get_admin_queryset(self):
        return self.queryset.order_by('-created_at')

    def get_standard_user_queryset(self, employee_profile):
        return self.queryset.filter(
            Q(id=employee_profile.id) | Q(manager=employee_profile)
        ).distinct().order_by('-created_at')


# ============================================================================
# HARD DELETE VIEWSETS (Use with caution - Permanent deletion)
# ============================================================================

@extend_schema(tags=['Departments (Hard Delete)'])
class DepartmentHardDeleteViewSet(BaseReadAuthWriteAdminViewSet):
    """
    Department Hard Delete.
    Access: Anyone authenticated can View. Only Admins can Create/Update/Delete.
    Delete operation permanently removes records from database.
    """
    queryset = Department.objects.all().order_by('name')
    serializer_class = DepartmentSerializer


@extend_schema(tags=['Employees (Hard Delete)'])
class EmployeeHardDeleteViewSet(AdminWritePermissionMixin, BaseRoleFilteredViewSet):
    """
    Employee Hard Delete.
    Access:
    - Admin: Full Access to all data.
    - Manager: View Self + Team subordinates.
    - Employee: View Self only.
    - Write Operations: Admin only (returns 403 otherwise).
    Delete operation permanently removes records from database.
    """
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    admin_forbidden_message = "Forbidden: Only Administrators have permission to manage employee profiles."

    def get_admin_queryset(self):
        return self.queryset.order_by('-created_at')

    def get_standard_user_queryset(self, employee_profile):
        return self.queryset.filter(
            Q(id=employee_profile.id) | Q(manager=employee_profile)
        ).distinct().order_by('-created_at')
