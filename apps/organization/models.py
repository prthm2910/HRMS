from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from apps.base.models import BaseModel
from apps.organization.constants import EmploymentType
import logging

logger = logging.getLogger(__name__)


class Department(BaseModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    # Human-Readable ID
    department_id = models.CharField(
        max_length=20, 
        unique=True, 
        editable=False,
        null=True,
        help_text="Format: DEPXXXXXX"
    )

    _display_id_prefix = 'DEP'
    _display_id_field = 'department_id'

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'
        db_table = 'departments'


class Employee(BaseModel):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='employee_profile'
    )

    # editable=False hides it from admin forms
    employee_id = models.CharField(
        max_length=20, 
        unique=True, 
        editable=False, 
        help_text="Auto-generated ID (e.g. EMP9A2B3C)"
    )
    
    department = models.ForeignKey(
        Department, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='employees'
    )
    
    designation = models.CharField(max_length=100)
    employment_type = models.CharField(
        max_length=20, 
        choices=EmploymentType.choices(), 
        default=EmploymentType.FULL_TIME.value
    )
    # Employment details
    joined_at = models.DateTimeField(help_text="Date and time when employee joined the organization")
    
    # Personal details
    born_at = models.DateTimeField(null=True, blank=True, help_text="Date and time of birth")
    salary = models.DecimalField(max_digits=10, decimal_places=2, help_text="Gross Monthly Salary")

    _display_id_prefix = 'EMP'
    _display_id_field = 'employee_id'

    manager = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='subordinates'
    )

    def __str__(self):
        return f"{self.user.username} ({self.employee_id})"

    class Meta:
        verbose_name = 'Employee'
        verbose_name_plural = 'Employees'
        db_table = 'employees'

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            logger.info(f"New employee profile saved | Employee ID: {self.employee_id} | User ID: {self.user.id}")
        else:
            logger.debug(f"Employee profile updated | Employee ID: {self.employee_id}")

    def clean(self):
    # 1. Prevent reporting to yourself
        if self.manager == self:
            logger.warning(f"Hierarchy validation failed | Self-reporting attempt | Employee ID: {self.employee_id}")
            raise ValidationError("You cannot report to yourself.")
        
        # 2. Prevent circular reporting (A -> B -> C -> A)
        # Using a hashset for O(N) cycle detection, with a safety depth limit.
        visited_managers = {self.id} if self.id else set()
        current_manager = self.manager
        depth = 0
        MAX_DEPTH = 500

        while current_manager:
            if current_manager.id in visited_managers:
                logger.warning(
                    f"Hierarchy validation failed | Circular reporting detected | "
                    f"Employee: {self.employee_id} -> Manager: {current_manager.employee_id}"
                )
                raise ValidationError("Circular reporting detected.")
            
            visited_managers.add(current_manager.id)
            current_manager = current_manager.manager
            depth += 1
            
            if depth > MAX_DEPTH:
                logger.error(f"Hierarchy validation failed | Maximum reporting depth exceeded | Employee: {self.employee_id}")
                raise ValidationError("Maximum reporting depth exceeded. Potential infinite loop or invalid hierarchy.")

class HOD(BaseModel):
    """
    Head of Department.
    Links an Employee to a Department they manage.
    """
    department = models.OneToOneField(
        Department,
        on_delete=models.CASCADE,
        related_name='hod'
    )
    employee = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name='hod_profile'
    )

    hod_id = models.CharField(
        max_length=20, 
        unique=True, 
        editable=False,
        null=True,
        help_text="Format: HODXXXXXX"
    )

    _display_id_prefix = 'HOD'
    _display_id_field = 'hod_id'

    def __str__(self):
        return f"HOD: {self.employee.user.username} - {self.department.name}"

    class Meta:
        verbose_name = "Head of Department"
        verbose_name_plural = "Heads of Department"
        db_table = "hods"