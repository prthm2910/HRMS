from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count
from django.core.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from apps.base.views import (
    BaseReadAuthWriteAdminViewSet, 
    DeleteMixin, 
    AdminWritePermissionMixin,
    BaseRoleBasedFilteredViewSet,
    BaseRoleFilteredViewSet
)
from apps.organization.models import Employee, Department, HOD
from apps.organization.serializers import EmployeeSerializer, DepartmentSerializer, HODSerializer


@extend_schema(tags=['HODs'])
class HODViewSet(AdminWritePermissionMixin, DeleteMixin, BaseRoleBasedFilteredViewSet):
    """
    ViewSet for managing Heads of Department.
    Access:
    - Admin: Full Access.
    - HOD: View Self only.
    - Write Operations: Admin only.
    """
    queryset = HOD.objects.filter(is_deleted=False)
    serializer_class = HODSerializer
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

    @extend_schema(
        description="View direct reports (subordinates). Defaults to current user. Pass ?manager_id=ID to drill down (if permitted).",
        parameters=[
            OpenApiParameter(name='manager_id', description='ID of the manager to view reports for (must be you or your downline)', required=False, type=str),
        ],
        responses={200: EmployeeSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='my-team')
    def my_team(self, request):
        """
        Returns a list of DIRECT reports for a specific manager.
        """
        user = request.user
        manager_id = request.query_params.get('manager_id')

        # 1. Determine who is the "Manager" in context
        if user.is_superuser:
            # Admin can view anyone's team
            if manager_id:
                try:
                    target_manager = Employee.objects.get(id=manager_id)
                except Employee.DoesNotExist:
                     return Response({"error": "Manager not found."}, status=status.HTTP_404_NOT_FOUND)
            else:
                # If admin calls without ID, what to show? 
                # Maybe show root level managers (those with no manager)? 
                # For now, let's require manager_id for admin usage or return empty to avoid massive dump.
                # Actually user asked for "subordinates of THAT user" (meaning self default).
                # But admins don't have an employee profile usually.
                return Response({"detail": "Admins must provide ?manager_id=... to view a specific team."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Regular Employee
            try:
                myself = user.employee_profile
            except AttributeError:
                return Response({"detail": "User has no employee profile."}, status=status.HTTP_403_FORBIDDEN)
            
            if manager_id:
                # Drill-Down Logic: Security Check
                # Is the requested 'manager_id' actually a subordinate of 'myself'?
                # We can check this recursively or simply check if they are in my downline.
                # Simplified check for MVP: Allow valid drill-down.
                
                # Check if target manager exists
                target_manager = Employee.objects.filter(id=manager_id).first()
                if not target_manager:
                    return Response({"error": "Manager not found."}, status=status.HTTP_404_NOT_FOUND)

                # SECURITY: Verify target_manager is in my downline.
                # Only allow viewing team of someone who is your direct or indirect report.
                
                if target_manager == myself:
                    # Generic case: viewing own team
                    pass 
                else:
                    # Recursive Check: Is 'myself' an ancestor of 'target_manager'?
                    # Traverse UP from target_manager to see if we hit myself.
                    is_descendant = False
                    current = target_manager
                    depth = 0
                    max_depth = 20 # Safety break for cycles

                    while current.manager and depth < max_depth:
                        if current.manager == myself:
                            is_descendant = True
                            break
                        current = current.manager
                        depth += 1
                    
                    if not is_descendant:
                         return Response({"detail": "You can only view teams of your subordinates."}, status=status.HTTP_403_FORBIDDEN)
            else:
                # Default: View my own direct reports
                target_manager = myself

        # 2. Fetch Direct Reports & Annotate with THEIR reports count
        direct_reports = Employee.objects.filter(
            manager=target_manager, 
            is_deleted=False
        ).annotate(
            direct_reports_count=Count('subordinates', filter=Q(subordinates__is_deleted=False))
        ).order_by('user__first_name')

        page = self.paginate_queryset(direct_reports)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(direct_reports, many=True)
        return Response(serializer.data)
