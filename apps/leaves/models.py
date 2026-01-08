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
        Calculates total WORKING DAYS only (Excludes Sat/Sun).
        """
        if not self.start_date or not self.end_date:
            return 0
        
        # 1. Total Calendar Days
        total_days = (self.end_date - self.start_date).days + 1
        
        working_days = 0
        for x in range(total_days):
            current_day = self.start_date + timedelta(days=x)
            
            # 2. Check if it's a Weekend
            # weekday(): 0=Monday, 4=Friday, 5=Saturday, 6=Sunday
            if current_day.weekday() < 5: 
                working_days += 1
                
        return working_days

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
    """
    employee = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE, 
        related_name='leave_balances'
    )
    leave_type = models.CharField(max_length=20, choices=LeaveRequest.LEAVE_TYPE_CHOICES)
    
    total_allocated = models.PositiveIntegerField(default=0)
    used_leaves = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('employee', 'leave_type')
        verbose_name_plural = "Leave Balances"
        db_table = 'leave_balances' 

    @property
    def remaining_leaves(self):
        return self.total_allocated - self.used_leaves

    def __str__(self):
        return f"{self.employee} - {self.leave_type}: {self.remaining_leaves} left"