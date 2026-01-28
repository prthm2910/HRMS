from rest_framework import filters 
from django_filters.rest_framework import DjangoFilterBackend
from apps.base.views import BaseRoleFilteredViewSet, SoftDeleteMixin, HardDeleteMixin
from apps.projects.models import Project, ProjectMember
from apps.projects.serializers import ProjectSerializer, ProjectMemberSerializer
from apps.projects.permissions import IsProjectAdminOrHODOrReadOnly


class ProjectViewSet(HardDeleteMixin, SoftDeleteMixin, BaseRoleFilteredViewSet):
    """
    ViewSet for managing Projects.
    Access:
    - Admin: Full Access.
    - HOD: Full Access to Projects in their Department.
    - Employee: View Projects they are a member of.
    """
    queryset = Project.objects.filter(is_deleted=False)
    serializer_class = ProjectSerializer
    permission_classes = [IsProjectAdminOrHODOrReadOnly]  # Custom Permission
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['department', 'project_type', 'parent_project']
    search_fields = ['name', 'department__name']
    ordering_fields = ['start_date', 'created_at']

    def get_standard_user_queryset(self, employee_profile):
        # 1. HOD Logic: If user is HOD, return all projects in their department
        if hasattr(employee_profile, 'hod_profile'):
            return self.queryset.filter(department=employee_profile.hod_profile.department)
        
        # 2. Employee Logic: Return projects where they are a member
        return self.queryset.filter(members__employee=employee_profile).distinct()

class ProjectMemberViewSet(HardDeleteMixin, SoftDeleteMixin, BaseRoleFilteredViewSet):
    """
    ViewSet for managing Project Members.
    Access:
    - Admin: Full Access.
    - HOD: Full Access to Members in their Department's Projects.
    - Employee: View Members in their own Projects.
    """
    queryset = ProjectMember.objects.filter(is_deleted=False)
    serializer_class = ProjectMemberSerializer
    permission_classes = [IsProjectAdminOrHODOrReadOnly]  # Custom Permission
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'employee', 'position', 'role']
    search_fields = ['employee__user__username', 'project__name', 'role']
    ordering_fields = ['date_of_joining']

    def get_standard_user_queryset(self, employee_profile):
        # 1. HOD Logic: Return members of all projects in their department
        if hasattr(employee_profile, 'hod_profile'):
            dept = employee_profile.hod_profile.department
            return self.queryset.filter(project__department=dept)
        
        # 2. Employee Logic: Return members of projects they belong to
        # (i.e., see their co-workers)
        my_projects = Project.objects.filter(members__employee=employee_profile)
        return self.queryset.filter(project__in=my_projects).distinct()
