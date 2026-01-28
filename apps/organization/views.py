from rest_framework import status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from apps.base.views import (
    BaseReadAuthWriteAdminViewSet, 
    SoftDeleteMixin, 
    AdminWritePermissionMixin,
    BaseRoleFilteredViewSet,
    HardDeleteMixin
)
from apps.organization.models import Employee, Department, HOD
from apps.organization.serializers import EmployeeSerializer, DepartmentSerializer, HODSerializer


class HODViewSet(HardDeleteMixin, AdminWritePermissionMixin, SoftDeleteMixin, BaseRoleFilteredViewSet):
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

@extend_schema(tags=['departments'])
class DepartmentViewSet(SoftDeleteMixin, BaseReadAuthWriteAdminViewSet):
    """
    Department Management.
    Access: Anyone authenticated can View. Only Admins can Create/Update/Delete.
    Default DELETE operation performs soft delete (marks as deleted).
    """
    queryset = Department.objects.filter(is_deleted=False).order_by('name')
    serializer_class = DepartmentSerializer

    @extend_schema(
        description="Permanently delete a department (superadmin only). This action cannot be undone.",
        responses={204: None, 403: None}
    )
    @action(detail=True, methods=['delete'], url_path='hard-delete')
    def hard_delete(self, request, pk=None):
        """Hard delete endpoint - permanently removes department from database."""
        if not request.user.is_superuser:
            return Response(
                {"detail": "Forbidden: Only superadmins can permanently delete records."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        department = self.get_object()
        department.delete()  # Permanent deletion
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['employees'])
class EmployeeViewSet(AdminWritePermissionMixin, SoftDeleteMixin, BaseRoleFilteredViewSet):
    """
    Employee Management.
    Access:
    - Admin: Full Access.
    - Manager: View Self + Team subordinates.
    - Employee: View Self only.
    - Write Operations: Admin only.
    Default DELETE operation performs soft delete (marks as deleted).
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

    @extend_schema(
        description="Permanently delete an employee (superadmin only). This action cannot be undone.",
        responses={204: None, 403: None}
    )
    @action(detail=True, methods=['delete'], url_path='hard-delete')
    def hard_delete(self, request, pk=None):
        """Hard delete endpoint - permanently removes employee from database."""
        if not request.user.is_superuser:
            return Response(
                {"detail": "Forbidden: Only superadmins can permanently delete records."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        employee = self.get_object()
        employee.delete()  # Permanent deletion
        return Response(status=status.HTTP_204_NO_CONTENT)
