import django_filters
from apps.holidays.models import Holiday

class HolidayFilter(django_filters.FilterSet):
    """
    Filter set for Holiday model.
    Supports filtering by region, date ranges, and status.
    """
    start_date = django_filters.DateTimeFilter(field_name='holiday_date', lookup_expr='gte')
    end_date = django_filters.DateTimeFilter(field_name='holiday_date', lookup_expr='lte')

    class Meta:
        model = Holiday
        fields = {
            'region': ['exact', 'icontains'],
            'is_recurring': ['exact'],
            'is_working_day': ['exact'],
            'is_active': ['exact'],
        }
