from django.db import models
from django.contrib.auth import get_user_model
from apps.audit.constants import AuditAction, AIOperationType, AIOperationLogStatus

User = get_user_model()


class AuditLog(models.Model):

    # Who did it?
    actor = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='audit_logs',
        help_text="The user who performed the action"
    )

    # What did they do?
    action = models.CharField(max_length=20, choices=AuditAction.choices())
    
    # Where did they do it? (Target Table & Row)
    table_name = models.CharField(max_length=50, help_text="The model name (e.g., 'Employee', 'LeaveRequest')")
    record_id = models.CharField(max_length=50, null=True, help_text="The ID of the modified record")

    # When?
    timestamp = models.DateTimeField(auto_now_add=True)

    # The Details (Old vs New values)
    changes = models.JSONField(null=True, blank=True, help_text="Stores 'old' and 'new' values for updates")

    # Client details (We removed IP Address as discussed)
    user_agent = models.CharField(max_length=255, null=True, blank=True, help_text="Browser or Client details")

    path = models.CharField(max_length=255, null=True, blank=True, help_text="The URL path")

    class Meta:
        db_table = 'audits'
        verbose_name = 'Audit'
        verbose_name_plural = 'Audits'        
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['table_name', 'record_id']),
            models.Index(fields=['actor']),
            models.Index(fields=['action']),
        ]

    def __str__(self):
        actor_name = self.actor.email if self.actor else "System/Unknown"
        return f"{actor_name} - {self.action} - {self.table_name}"

    # --- THE MAGIC: Helper to detect source for Admin Panel ---
    @property
    def request_source(self):
        """
        Parses the User Agent to return a clean Source Name.
        """
        path = self.path or ""
        ua = self.user_agent or ""

        # 1. Check Path specific signatures first
        if path.startswith('/admin/'):
            return "Admin Panel"
        
        if "Postman" in ua:
            return "Postman Client"
        elif "Mozilla" in ua or "Chrome" in ua or "Safari" in ua or "Edge" in ua:
            return "Browser"
        elif "Python" in ua or "requests" in ua:
            return "Python Script"
        else:
            return "Unknown Source"


# AI Operation Choices are moved to constants.py


class AIOperationLog(models.Model):
    """
    Detailed logs for AI service operations.
    Linked to AuditLog via OneToOneField for nested audit trail.
    """
    
    # Link to parent audit entry
    audit_log = models.OneToOneField(
        AuditLog,
        on_delete=models.CASCADE,
        related_name='ai_operation',
        help_text="Parent audit log entry"
    )
    
    # AI operation details
    operation_type = models.CharField(
        max_length=50,
        choices=AIOperationType.choices,
        help_text="Type of AI operation performed"
    )
    
    model_used = models.CharField(
        max_length=100,
        help_text="AI model used (e.g., 'gemini-3-flash-preview', 'gpt-4')"
    )
    
    # Input/Output data
    input_data = models.JSONField(
        help_text="Summary of input data (e.g., image path, text snippet)"
    )
    
    output_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Summary of output data (e.g., extracted entities, classification results)"
    )
    
    # Status and performance
    status = models.CharField(
        max_length=20,
        choices=AIOperationLogStatus.choices(),
        default=AIOperationLogStatus.PENDING.value
    )
    
    processing_time_seconds = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="Processing time in seconds (e.g., 1.245 seconds)"
    )
    
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text="Error message if operation failed"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ai_operation_logs'
        verbose_name = 'AI Operation Log'
        verbose_name_plural = 'AI Operation Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['operation_type', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.operation_type} - {self.status} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"