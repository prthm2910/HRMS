from django.db import models
from apps.base.models import BaseTemplateModel
from apps.organization.models import Department, Employee

class Project(BaseTemplateModel):
    """
    Represents a project or functional workgroup within a department.
    """
    class ProjectType(models.TextChoices):
        PERMANENT = 'PERMANENT', 'Permanent'
        PROJECT = 'PROJECT', 'Project Based'

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
        choices=ProjectType.choices, 
        default=ProjectType.PERMANENT
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    
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


class ProjectMember(BaseTemplateModel):
    """
    Represents an employee's membership in a project.
    """
    class Position(models.TextChoices):
        LEADER = 'LEADER', 'Project Leader'
        CO_LEADER = 'CO_LEADER', 'Co-Leader'
        MEMBER = 'MEMBER', 'Member'

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
        choices=Position.choices, 
        default=Position.MEMBER
    )
    
    date_of_joining = models.DateField()
    date_of_leaving = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.employee.user.username} - {self.project.name} ({self.position})"

    class Meta:
        db_table = "project_members"
        unique_together = ['project', 'employee']
