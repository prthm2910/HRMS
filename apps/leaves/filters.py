import django_filters
from apps.leaves.models import LeaveRequest, LeaveRequestStatus

class LeaveRequestFilter(django_filters.FilterSet):
    """
    Filter set for LeaveRequest model.
    Supports filtering by status, leave_type, and specific month/year.
    """
    month = django_filters.NumberFilter(field_name='started_at', lookup_expr='month')
    year = django_filters.NumberFilter(field_name='started_at', lookup_expr='year')

    class Meta:
        model = LeaveRequest
        fields = {
            'status': ['exact'],
            'leave_type': ['exact'],
            'employee': ['exact'],
            'is_half_day': ['exact'],
        }


class SubordinateLeaveRequestFilter(LeaveRequestFilter):
    """
    Specialized filter for manager view of subordinate requests.
    Defaults to PENDING status if none is provided.
    Supports ?status=all to remove the status filter.
    """
    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            # We must copy the QueryDict to make it mutable
            data = data.copy()
            status_param = data.get('status')
            
            # 1. If status is MISSING, default to PENDING
            if status_param is None:
                data['status'] = LeaveRequestStatus.PENDING.value
            
            # 2. If status is 'all', remove the filter entirely
            elif str(status_param).lower() == 'all':
                data.pop('status', None)
                
        super().__init__(data, *args, **kwargs)
