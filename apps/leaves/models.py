from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from datetime import timedelta  # <--- NEW IMPORT
from base.models import BaseTemplateModel
from organization.models import Employee

class LeaveRequest(BaseTemplateModel):
    # Enums for Dropdowns
    LEAVE_TYPE_CHOICES = [
        ('SICK', 'Sick Leave'),
        ('CASUAL', 'Casual Leave'),
        ('EARNED', 'Earned/Privilege Leave'),
        ('UNPAID', 'Loss of Pay (LWP)'),
    ]

    HALF_DAY_PERIOD_CHOICES = [
        ('FIRST_HALF', 'First Half'),
        ('SECOND_HALF', 'Second Half'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
    ]

    # 1. Who and What
    employee = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE, 
        related_name='leave_requests'
    )
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES)
    
    # 2. When
    start_date = models.DateField()
    end_date = models.DateField()
    
    # 2.1 Half-Day Support
    is_half_day = models.BooleanField(default=False, help_text="Is this a half-day leave?")
    half_day_period = models.CharField(
        max_length=20, 
        choices=HALF_DAY_PERIOD_CHOICES, 
        blank=True, 
        null=True,
        help_text="Which half of the day (required if is_half_day=True)"
    )
    
    # 3. Why
    reason = models.TextField(help_text="Reason for leave")
    
    # 4. Approval Workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    action_by = models.ForeignKey(
        Employee, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='processed_leaves'
    )
    rejection_reason = models.TextField(blank=True, null=True)

    @property
    def duration(self):
        """
        Calculates actual leave duration considering half-days.
        Returns decimal: 0.5 for half-day, working days (float) for full-day.
        Excludes weekends (Sat/Sun).
        """
        if self.is_half_day:
            return 0.5
        
        if not self.start_date or not self.end_date:
            return 0.0
        
        # Calculate working days (excluding weekends)
        total_days = (self.end_date - self.start_date).days + 1
        working_days = 0
        
        for x in range(total_days):
            current_day = self.start_date + timedelta(days=x)
            # weekday(): 0=Monday, 4=Friday, 5=Saturday, 6=Sunday
            if current_day.weekday() < 5: 
                working_days += 1
                
        return float(working_days)

    def clean(self):
        """Validation Logic"""
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError(_("End date cannot be before start date."))
        
        # Half-day validations
        if self.is_half_day:
            if self.start_date != self.end_date:
                raise ValidationError(_("Half-day leave must have the same start and end date."))
            if not self.half_day_period:
                raise ValidationError(_("Half-day period (First Half/Second Half) is required for half-day leaves."))

    def __str__(self):
        return f"{self.employee} - {self.leave_type} ({self.status})"

    class Meta:
        verbose_name_plural = "Leave Requests"
        db_table = 'leave_requests'


class LeaveBalance(BaseTemplateModel):
    """
    Tracks how many leaves an employee has available.
    """
    employee = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE, 
        related_name='leave_balances'
    )
    leave_type = models.CharField(max_length=20, choices=LeaveRequest.LEAVE_TYPE_CHOICES)
    
    total_allocated = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    used_leaves = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    class Meta:
        unique_together = ('employee', 'leave_type')
        verbose_name_plural = "Leave Balances"
        db_table = 'leave_balances' 

    @property
    def remaining_leaves(self):
        return self.total_allocated - self.used_leaves

    def __str__(self):
        return f"{self.employee} - {self.leave_type}: {self.remaining_leaves} left"