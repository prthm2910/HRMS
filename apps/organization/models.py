import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from users.models import BaseTemplateModel

class Department(BaseTemplateModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'
        db_table = 'departments'

class Employee(BaseTemplateModel):
    EMPLOYMENT_TYPE_CHOICES = [
        ('FULL_TIME', 'Full Time'),
        ('PART_TIME', 'Part Time'),
        ('CONTRACT', 'Contract'),
        ('INTERN', 'Intern'),
    ]

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
        choices=EMPLOYMENT_TYPE_CHOICES, 
        default='FULL_TIME'
    )

    date_of_joining = models.DateField()
    date_of_birth = models.DateField(null=True, blank=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, help_text="Gross Monthly Salary")

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
        # Auto-generate ID if it doesn't exist
        if not self.employee_id:
            while True:
                # Generates a random hex string (e.g., 'a1b2c3')
                # .hex[:6] takes the first 6 characters.
                random_suffix = uuid.uuid4().hex[:6].upper()
                
                # Format: EMP + RandomString (No hyphen) -> EMPA1B2C3
                new_id = f"EMP{random_suffix}"
                
                # Check if this ID already exists to prevent duplicates
                if not Employee.objects.filter(employee_id=new_id).exists():
                    self.employee_id = new_id
                    break
        
        super().save(*args, **kwargs)

    def clean(self):
    # 1. Prevent reporting to yourself
        if self.manager == self:
            raise ValidationError("You cannot report to yourself.")
        
        # 2. Prevent simple cycles (A -> B -> A)
        # Note: For deep cycles (A->B->C->A), you need more complex logic, 
        # but strictly checking immediate parent is the bare minimum.
        if self.manager and self.manager.manager == self:
            raise ValidationError("Circular reporting detected.")    