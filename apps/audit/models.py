from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('HARD_DELETE', 'Hard Delete 💥'),
    ]

    # Who did it?
    actor = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='audit_logs',
        help_text="The user who performed the action"
    )

    # What did they do?
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    
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