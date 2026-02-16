from django.db import models
from apps.base.models import BaseModel
from apps.organization.models import Department, Employee
from apps.projects.constants import ProjectType, Position

class Project(BaseModel):
    """
    Represents a project or functional workgroup within a department.
    """
    # Project type and Duration

    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='projects'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    # Project type and Duration
    project_type = models.CharField(
        max_length=20, 
        choices=ProjectType.choices(), 
        default=ProjectType.PERMANENT.value
    )
    started_at = models.DateTimeField(help_text="Project start date and time")
    ended_at = models.DateTimeField(null=True, blank=True, help_text="Project end date and time")
    
    # Hierarchy
    parent_project = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sub_projects'
    )
    
    def __str__(self):
        return f"{self.name} ({self.department.name})"

    class Meta:
        db_table = "projects"


class ProjectMember(BaseModel):
    """
    Represents an employee's membership in a project.
    """
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='members'
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='project_memberships'
    )
    
    # "Role" -> Functional Role (e.g., Backend Dev)
    role = models.CharField(max_length=100, help_text="Functional role e.g. Backend Dev, Designer")
    
    # "Position" -> Hierarchy Rank (e.g., Leader, Member)
    position = models.CharField(
        max_length=20, 
        choices=Position.choices(), 
        default=Position.MEMBER.value
    )
    
    
    joined_at = models.DateTimeField(help_text="Date and time when member joined the project")
    left_at = models.DateTimeField(null=True, blank=True, help_text="Date and time when member left the project")

    def __str__(self):
        return f"{self.employee.user.username} - {self.project.name} ({self.position})"

    class Meta:
        db_table = "project_members"
        unique_together = ['project', 'employee']
