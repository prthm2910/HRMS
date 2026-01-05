from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from users.models import BaseTemplateModel
from organization.models import Employee

class LeaveRequest(BaseTemplateModel):
    # Enums for Dropdowns
    LEAVE_TYPE_CHOICES = [
        ('SICK', 'Sick Leave'),
        ('CASUAL', 'Casual Leave'),
        ('EARNED', 'Earned/Privilege Leave'),
        ('UNPAID', 'Loss of Pay (LWP)'),
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
    
    # 3. Why
    reason = models.TextField(help_text="Reason for leave")
    
    # 4. Approval Workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Who approved/rejected it? (Usually the Manager)
    action_by = models.ForeignKey(
        Employee, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='processed_leaves'
    )
    rejection_reason = models.TextField(blank=True, null=True)

    # inherited: id, created_at, updated_at...

    @property
    def duration(self):
        """Calculates total days (inclusive)"""
        if self.start_date and self.end_date:
            delta = self.end_date - self.start_date
            return delta.days + 1
        return 0

    def clean(self):
        """Validation Logic"""
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError(_("End date cannot be before start date."))

    def __str__(self):
        return f"{self.employee} - {self.leave_type} ({self.status})"

    class Meta:
        verbose_name_plural = "Leave Requests"
        db_table = 'leave_requests'


class LeaveBalance(BaseTemplateModel):
    """
    Tracks how many leaves an employee has available.
    One row per Employee per Leave Type.
    """
    employee = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE, 
        related_name='leave_balances'
    )
    leave_type = models.CharField(max_length=20, choices=LeaveRequest.LEAVE_TYPE_CHOICES)
    
    # The Math
    total_allocated = models.PositiveIntegerField(default=0, help_text="Total leaves given per year")
    used_leaves = models.PositiveIntegerField(default=0, help_text="Approved leaves taken so far")

    class Meta:
        # Ensures one employee can't have two rows for "Sick Leave"
        unique_together = ('employee', 'leave_type')
        verbose_name_plural = "Leave Balances"
        db_table = 'leave_balances' 

    @property
    def remaining_leaves(self):
        return self.total_allocated - self.used_leaves

    def __str__(self):
        return f"{self.employee} - {self.leave_type}: {self.remaining_leaves} left"