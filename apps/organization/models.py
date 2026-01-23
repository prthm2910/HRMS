import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from apps.base.models import BaseTemplateModel


class Department(BaseTemplateModel):
    """
    1. FIRST PRINCIPLES: The "Office Silo"
    Every company has different functional groups (HR, IT, Sales). A 
    Department is just a container to group employees together so you 
    can manage them as a unit.

    2. TECHNICAL BREAKDOWN:
    - BaseTemplateModel: Inherits our primary key (UUID) and timestamps.
    - name: A simple label for the department.
    - TextChoices (below): Defines a strict list of allowed values for 
      employment status, preventing typos.
    """
    name = models.CharField(max_length=100)
    # null=True: Database-level (allows NULL in DB) | blank=True: Validation-level (allows empty in Forms/Admin)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        """
        1. FIRST PRINCIPLES: The "Label on the Folder"
        When you look at a list of departments in the admin panel, you don't 
        want to see a random code like 'Dept-Object (5)'. You want to see 
        the name (e.g., "Human Resources"). This method tells Django 
        exactly what to use as the human-readable label.

        2. TECHNICAL BREAKDOWN:
        - __str__: A special Python "magic method" that returns a string 
          representation of an object.
        - self.name: We choose the 'name' field as the default display value.
        """
        return self.name
    
    class Meta:
        """
        1. FIRST PRINCIPLES: The "Filing Instructions"
        The 'Meta' class is where you give the database specific instructions 
        on how to file this information. It's like telling a clerk: 
        "Call this folder 'Department', and put it in a drawer labeled 'departments'."

        2. TECHNICAL BREAKDOWN:
        - verbose_name: The "friendly" name used in the Admin for 1 item.
        - verbose_name_plural: The "friendly" name used for multiple items.
        - db_table: Explicitly names the table in your PostgreSQL database.
        """
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'
        db_table = 'departments'


class EmploymentType(models.TextChoices):
    """Employment type choices for Employee model"""
    FULL_TIME = 'FULL_TIME', 'Full Time'
    PART_TIME = 'PART_TIME', 'Part Time'
    CONTRACT = 'CONTRACT', 'Contract'
    INTERN = 'INTERN', 'Intern'


class Employee(BaseTemplateModel):

    """
    1. FIRST PRINCIPLES: "Account vs. Identity"
    Imagine you have a login for Facebook. That's your "Account" (User). 
    But then you join a specific group for your job. That group has your 
    job title, salary, and boss. That's your "Employee Profile". 
    In this app, one person can have exactly one profile.

    2. TECHNICAL BREAKDOWN:
    - OneToOneField: Ensures 1 User = 1 Employee. You can't have two employee 
      profiles for the same login.
    - AUTH_USER_MODEL: Points to our custom User model in 'apps/users'.
    - on_delete=models.CASCADE: If the User account is deleted, the Employee 
      profile is also automatically deleted.
    - related_name='employee_profile': Let's you find the profile from the 
      user object (e.g., request.user.employee_profile).
    """
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
    
    """
    1. FIRST PRINCIPLES: The "Reporting Structure"
    An employee doesn't just work for the company; they work in a specific 
    spot. The Department is where they sit, and the Designation is what 
    their name tag says.

    2. TECHNICAL BREAKDOWN:
    - ForeignKey: A "Many-to-One" relationship. One department has many 
      employees, but each employee belongs to exactly one (or zero) department.
    - SET_NULL: If a department is deleted, the employee isn't deleted; 
      their department field just becomes empty.
    - related_name='employees': Let's you find all employees in a department 
      from the department object (e.g., department_obj.employees.all()).
    - null=True: Database-level (allows NULL in DB) | blank=True: Validation-level (allows empty in Forms/Admin)
    """
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
        choices=EmploymentType.choices, 
        default=EmploymentType.FULL_TIME
    )
    date_of_joining = models.DateField()
# - null=True: Database-level (allows NULL in DB) | blank=True: Validation-level (allows empty in Forms/Admin)
    date_of_birth = models.DateField(null=True, blank=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, help_text="Gross Monthly Salary")

    """
    1. FIRST PRINCIPLES: The "Boss System"
    In a company, almost everyone reports to someone. The 'manager' field 
    is special because it points back to another row in this same table. 
    It's like a family tree where an employee points to their parent.

    2. TECHNICAL BREAKDOWN:
    - ForeignKey('self'): A self-referential relationship. It allows an 
      Employee object to link to another Employee object.
    - related_name='subordinates': Allows you to do 'manager_obj.subordinates.all()' 
      to find everyone who reports to that manager.
    """
    manager = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='subordinates'
    )

    def __str__(self):
        """
        1. FIRST PRINCIPLES: The "Passport ID"
        This is the default way an employee is identified in the system. 
        It combines their username and their unique employee ID.
        """
        return f"{self.user.username} ({self.employee_id})"

    class Meta:
        """
        1. FIRST PRINCIPLES: The "Individual Dossier"
        Tells Django that these records should be called 'Employee' and 
        stored in the 'employees' table.
        """
        verbose_name = 'Employee'
        verbose_name_plural = 'Employees'
        db_table = 'employees'

    def save(self, *args, **kwargs):
        """
        1. FIRST PRINCIPLES: The "Automatic Stamp"
        Every employee needs a unique ID badge (like EMP123). Instead of 
        making the HR person type it manually, the computer generates a 
        random, guaranteed unique one every time a new profile is created.

        2. TECHNICAL BREAKDOWN:
        - uuid.uuid4(): Generates a globally unique random ID.
        - .hex[:6]: We take only the first 6 characters of that ID to keep 
          it short and readable.
        - filter(...).exists(): A safety check to make sure we didn't 
          accidentally generate the same ID twice (highly unlikely but 
          important for production).
        """
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
        """
        1. FIRST PRINCIPLES: "Checking for Logic Loops"
        You can't be your own boss, and you can't report to someone who 
        reports to you (that would be a loop!). This 'clean' step is the 
        final check before the data is saved to make sure it makes sense.

        2. TECHNICAL BREAKDOWN:
        - clean(): A Django method for cross-field validation.
        - ValidationError: Stops the save process and shows a helpful error 
          message in the Admin or API.
        - self.manager == self: Prevents self-reporting.
        - self.manager.manager == self: Prevents simple circular reporting 
          (A reporting to B who reports to A).
        """
        # 1. Prevent reporting to yourself
        if self.manager == self:
            raise ValidationError("You cannot report to yourself.")
        
        # 2. Prevent simple cycles (A -> B -> A)
        # Note: For deep cycles (A->B->C->A), you need more complex logic, 
        # but strictly checking immediate parent is the bare minimum.
        if self.manager and self.manager.manager == self:
            raise ValidationError("Circular reporting detected.")    