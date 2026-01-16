"""
Common utility functions used across the HRMS application.
"""
from datetime import timedelta, date
import threading

_thread_locals = threading.local()


def calculate_working_days(start_date, end_date, region=None):
    """
    Calculate working days between two dates (excluding weekends and holidays).
    
    Args:
        start_date (date): Start date
        end_date (date): End date
        region (str, optional): Region to filter holidays (e.g., 'Mumbai', 'All India')
        
    Returns:
        tuple: (working_days, excluded_holidays)
            - working_days (int): Number of working days (Monday-Friday, excluding holidays)
            - excluded_holidays (list): List of dicts with holiday info that were excluded
        
    Example:
        >>> from datetime import date
        >>> calculate_working_days(date(2026, 2, 20), date(2026, 2, 23))
        (2, [])  # Friday and Monday (skips Sat/Sun), no holidays
        
        >>> calculate_working_days(date(2026, 1, 24), date(2026, 1, 28))
        (4, [{'date': '2026-01-26', 'name': 'Republic Day'}])  # Excludes Jan 26 holiday
    """
    if not start_date or not end_date:
        return 0, []
    
    # Get active holidays in the date range
    # Import here to avoid circular imports
    from apps.holidays.models import Holiday
    
    holidays_query = Holiday.objects.filter(
        date__gte=start_date,
        date__lte=end_date,
        is_active=True,
        is_deleted=False
    )
    
    # Filter by region if provided
    if region:
        holidays_query = holidays_query.filter(region=region)
    
    # Get holiday dates
    holiday_dates = set(holidays_query.values_list('date', flat=True))
    
    # Get holiday details for notification
    excluded_holidays = []
    for holiday in holidays_query:
        excluded_holidays.append({
            'date': str(holiday.date),
            'name': holiday.name,
            'region': holiday.region or 'All'
        })
    
    total_days = (end_date - start_date).days + 1
    working_days = 0
    
    for x in range(total_days):
        current_day = start_date + timedelta(days=x)
        # weekday(): 0=Monday, 4=Friday, 5=Saturday, 6=Sunday
        is_weekday = current_day.weekday() < 5
        is_holiday = current_day in holiday_dates
        
        # Count as working day if it's a weekday AND not a holiday
        if is_weekday and not is_holiday:
            working_days += 1
            
    return working_days, excluded_holidays


def is_weekend(check_date):
    """
    Check if a date falls on a weekend.
    
    Args:
        check_date (date): Date to check
        
    Returns:
        bool: True if Saturday or Sunday, False otherwise
        
    Example:
        >>> from datetime import date
        >>> is_weekend(date(2026, 1, 10))  # Saturday
        True
        >>> is_weekend(date(2026, 1, 12))  # Monday
        False
    """
    return check_date.weekday() >= 5  # 5=Saturday, 6=Sunday


def get_employee_profile(user):
    """
    Get employee profile from user object.
    Handles both 'employee_profile' and 'employee' attributes.
    
    Args:
        user: Django User object
        
    Returns:
        Employee: Employee instance or None
        
    Example:
        >>> employee = get_employee_profile(request.user)
        >>> if employee:
        ...     print(employee.employee_id)
    """
    return getattr(user, 'employee_profile', None) or getattr(user, 'employee', None)

def set_audit_data(user, user_agent, path):
    """Store user, user_agent, and path in the current thread."""
    _thread_locals.current_user = user
    _thread_locals.current_user_agent = user_agent
    _thread_locals.current_path = path  # <--- Store the path

def get_audit_data():
    """Retrieve data as a dictionary."""
    return {
        'user': getattr(_thread_locals, 'current_user', None),
        'user_agent': getattr(_thread_locals, 'current_user_agent', ''),
        'path': getattr(_thread_locals, 'current_path', '') # <--- Retrieve the path
    }

def clear_audit_data():
    """Clean up."""
    if hasattr(_thread_locals, 'current_user'):
        del _thread_locals.current_user
    if hasattr(_thread_locals, 'current_user_agent'):
        del _thread_locals.current_user_agent
    if hasattr(_thread_locals, 'current_path'):
        del _thread_locals.current_path