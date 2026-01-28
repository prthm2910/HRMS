from rest_framework import filters
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from apps.base.views import (
    BaseReadAuthWriteAdminViewSet, 
    DeleteMixin, 
    AdminWritePermissionMixin,
    BaseRoleFilteredViewSet
)
from apps.organization.models import Employee, Department, HOD
from apps.organization.serializers import EmployeeSerializer, DepartmentSerializer, HODSerializer


@extend_schema(tags=['HODs'])
class HODViewSet(AdminWritePermissionMixin, DeleteMixin, BaseRoleFilteredViewSet):
    """
    ViewSet for managing Heads of Department.
    Access:
    - Admin: Full Access.
    - HOD: View Self only.
    - Write Operations: Admin only.
    """
    queryset = HOD.objects.filter(is_deleted=False)
    serializer_class = HODSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['department', 'employee']
    search_fields = ['employee__user__username', 'department__name']
    ordering_fields = ['created_at']
    admin_forbidden_message = "Forbidden: Only Administrators can manage HOD assignments."

    def get_standard_user_queryset(self, employee_profile):
        # Regular users can only see their own HOD record if they are one
        return self.queryset.filter(employee=employee_profile)

@extend_schema(tags=['Departments'])
class DepartmentViewSet(DeleteMixin, BaseReadAuthWriteAdminViewSet):
    """
    Department Management.
    Access: Anyone authenticated can View. Only Admins can Create/Update/Delete.
    Default DELETE operation performs soft delete (marks as deleted).
    Admin can perform HARD delete with ?force=true.
    """
    queryset = Department.objects.filter(is_deleted=False).order_by('name')
    serializer_class = DepartmentSerializer


@extend_schema(tags=['Employees'])
class EmployeeViewSet(AdminWritePermissionMixin, DeleteMixin, BaseRoleFilteredViewSet):
    """
    Employee Management.
    Access:
    - Admin: Full Access.
    - Manager: View Self + Team subordinates.
    - Employee: View Self only.
    - Write Operations: Admin only.
    Default DELETE operation performs soft delete (marks as deleted).
    Admin can perform HARD delete with ?force=true.
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
