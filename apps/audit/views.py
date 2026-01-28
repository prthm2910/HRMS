from apps.audit.models import AuditLog
from apps.audit.serializers import AuditLogSerializer
from apps.base.views import BaseReadOnlyAdminViewSet
from drf_spectacular.utils import extend_schema

@extend_schema(tags=['System - Audit Logs'])
class AuditLogViewSet(BaseReadOnlyAdminViewSet):
    """
    Read-Only ViewSet for Audit Logs.
    We use ReadOnlyModelViewSet because logs should NEVER be edited or deleted via API.
    Only Admins (is_staff=True) can view these logs.
    """
    queryset = AuditLog.objects.all().order_by('-created_at')
    serializer_class = AuditLogSerializer