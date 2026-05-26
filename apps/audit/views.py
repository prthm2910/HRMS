from apps.audit.models import AuditLog
from apps.audit.serializers import AuditLogSerializer
from apps.base.views import BaseReadOnlyAdminFilteredViewSet
from drf_spectacular.utils import extend_schema

@extend_schema(tags=['System - Audit Logs'])
class AuditLogViewSet(BaseReadOnlyAdminFilteredViewSet):
    """
    Read-Only ViewSet for Audit Logs.
    We use ReadOnlyModelViewSet because logs should NEVER be edited or deleted via API.
    Only Admins (is_staff=True) can view these logs.
    """
    queryset = AuditLog.objects.all().order_by('-timestamp')
    serializer_class = AuditLogSerializer
    filterset_fields = ['actor', 'action', 'table_name']
    search_fields = ['record_id', 'actor__email', 'table_name']
    ordering_fields = ['timestamp']