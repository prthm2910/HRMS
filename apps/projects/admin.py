from django.contrib import admin
from apps.projects.models import Project, ProjectMember

class ProjectMemberInline(admin.TabularInline):
    model = ProjectMember
    extra = 1

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('project_id', 'name', 'department', 'project_type', 'started_at', 'parent_project')
    list_filter = ('department', 'project_type', 'started_at')
    search_fields = ('name', 'department__name')
    inlines = [ProjectMemberInline]

@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ('project_member_id', 'employee', 'project', 'role', 'position', 'joined_at', 'is_active')
    list_filter = ('project', 'position', 'is_active')
    search_fields = ('employee__user__username', 'project__name', 'role')
