import logging
from drf_spectacular.utils import extend_schema
from apps.base.views import RoleFullViewSet, DeleteMixin
from apps.projects.models import Project, ProjectMember
from apps.projects.serializers import ProjectSerializer, ProjectMemberSerializer
from apps.projects.permissions import IsProjectAdminOrHODOrReadOnly

logger = logging.getLogger(__name__)


@extend_schema(tags=['Projects'])
class ProjectViewSet(DeleteMixin, RoleFullViewSet):
    """
    ViewSet for managing Projects.
    Access:
    - Admin: Full Access to all projects. Must specify department when creating.
    - HOD: Full Access to Projects in their Department. Department is auto-detected.
    - Employee: View Projects they are a member of. Cannot create projects.
    """
    queryset = Project.objects.filter(is_deleted=False).select_related('department', 'parent_project')
    serializer_class = ProjectSerializer
    permission_classes = [IsProjectAdminOrHODOrReadOnly]  # Custom Permission
    filterset_fields = ['department', 'project_type', 'parent_project']
    search_fields = ['name', 'department__name']
    ordering_fields = ['started_at', 'created_at']

    def get_standard_user_queryset(self, employee_profile):
        # 1. HOD Logic: If user is HOD, return all projects in their department
        if hasattr(employee_profile, 'hod_profile'):
            dept_id = employee_profile.hod_profile.department_id
            logger.debug(f"Fetching projects via HOD context | User ID: {employee_profile.user_id} | Dept ID: {dept_id}")
            return self.queryset.filter(department_id=dept_id)
        
        # 2. Employee Logic: Return projects where they are a member
        logger.debug(f"Fetching projects via Employee context | User ID: {employee_profile.user_id}")
        return self.queryset.filter(members__employee=employee_profile).distinct()

@extend_schema(tags=['Project Members'])
class ProjectMemberViewSet(DeleteMixin, RoleFullViewSet):
    """
    ViewSet for managing Project Members.
    Access:
    - Admin: Full Access.
    - HOD: Full Access to Members in their Department's Projects.
    - Employee: View Members in their own Projects.
    """
    queryset = ProjectMember.objects.filter(is_deleted=False).select_related('project', 'employee__user')
    serializer_class = ProjectMemberSerializer
    permission_classes = [IsProjectAdminOrHODOrReadOnly]  # Custom Permission
    filterset_fields = ['project', 'employee', 'position', 'role']
    search_fields = ['employee__user__username', 'project__name', 'role']
    ordering_fields = ['joined_at']

    def get_standard_user_queryset(self, employee_profile):
        # 1. HOD Logic: Return members of all projects in their department
        if hasattr(employee_profile, 'hod_profile'):
            dept_id = employee_profile.hod_profile.department_id
            logger.debug(f"Fetching project members via HOD context | User ID: {employee_profile.user_id} | Dept ID: {dept_id}")
            return self.queryset.filter(project__department_id=dept_id)
        
        logger.debug(f"Fetching project members via Employee context | User ID: {employee_profile.user_id}")
        return self.queryset.filter(project__members__employee=employee_profile).distinct()
