import django_filters
from apps.leaves.models import LeaveRequest

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
