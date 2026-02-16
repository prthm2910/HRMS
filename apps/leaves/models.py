from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.base.models import BaseModel
from apps.base.utils import calculate_working_and_non_working_days
from apps.organization.models import Employee
from apps.leaves.constants import LeaveType, HalfDayPeriod, LeaveRequestStatus


class LeaveRequest(BaseModel):
    # 1. Who and What
    employee = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE, 
        related_name='leave_requests'
    )
    leave_type = models.CharField(max_length=20, choices=LeaveType.choices())
    # 2. When
    started_at = models.DateTimeField(help_text="Start date and time of leave")
    ended_at = models.DateTimeField(help_text="End date and time of leave")
    
    # 2.1 Half-Day Support
    is_half_day = models.BooleanField(default=False, help_text="Is this a half-day leave?")
    half_day_period = models.CharField(
        max_length=20, 
        choices=HalfDayPeriod.choices(), 
        blank=True, 
        null=True,
        help_text="Which half of the day (required if is_half_day=True)"
    )
    
    # 3. Why
    reason = models.TextField(help_text="Reason for leave")
    
    # 4. Approval Workflow
    status = models.CharField(max_length=20, choices=LeaveRequestStatus.choices(), default=LeaveRequestStatus.PENDING.value)
    
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
        Calculates actual leave duration considering half-days and holidays.
        Returns decimal: 0.5 for half-day, working days (float) for full-day.
        Excludes weekends (Sat/Sun) and holidays.
        """
        if self.is_half_day:
            return 0.5
        
        if not self.started_at or not self.ended_at:
            return 0.0
        
        # Use utility function for working days calculation (returns tuple)
        # Convert datetime to date for calculation
        res = calculate_working_and_non_working_days(self.started_at.date(), self.ended_at.date())
        return float(res['working_days'])


    def clean(self):
        """Validation Logic"""
        if self.started_at and self.ended_at and self.started_at.date() > self.ended_at.date():
            raise ValidationError(_("End date cannot be before start date."))
        
        # Half-day validations
        if self.is_half_day:
            if self.started_at.date() != self.ended_at.date():
                raise ValidationError(_("Half-day leave must have the same start and end date."))
            if not self.half_day_period:
                raise ValidationError(_("Half-day period (First Half/Second Half) is required for half-day leaves."))

    def __str__(self):
        return f"{self.employee} - {self.leave_type} ({self.status})"

    class Meta:
        verbose_name_plural = "Leave Requests"
        db_table = 'leave_requests'


class LeaveBalance(BaseModel):
    """
    Tracks how many leaves an employee has available.
    """
    employee = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE, 
        related_name='leave_balances'
    )
    leave_type = models.CharField(max_length=20, choices=LeaveType.choices())
    
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