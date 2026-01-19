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


def is_holiday(check_date, region=None):
    """
    Check if a date is a declared holiday.
    
    Args:
        check_date (date): Date to check
        region (str, optional): Region to filter holidays (e.g., 'Mumbai', 'All India')
        
    Returns:
        tuple: (is_holiday, holiday_info)
            - is_holiday (bool): True if the date is a holiday, False otherwise
            - holiday_info (dict): Holiday details if found, None otherwise
        
    Example:
        >>> from datetime import date
        >>> is_holiday(date(2026, 1, 26))
        (True, {'name': 'Republic Day', 'description': '...', 'region': 'All India'})
        >>> is_holiday(date(2026, 1, 27))
        (False, None)
    """
    from apps.holidays.models import Holiday
    
    try:
        holiday_query = Holiday.objects.filter(
            date=check_date,
            is_active=True,
            is_deleted=False
        )
        
        # Filter by region if provided
        if region:
            holiday_query = holiday_query.filter(region=region)
        
        holiday = holiday_query.first()
        
        if holiday:
            return True, {
                'name': holiday.name,
                'description': holiday.description,
                'region': holiday.region or 'All India'
            }
        return False, None
    except Exception:
        return False, None


def get_non_working_days_info(start_date, end_date, region=None):
    """
    Get detailed information about holidays and weekends in a date range.
    
    Args:
        start_date (date): Start date
        end_date (date): End date
        region (str, optional): Region to filter holidays
        
    Returns:
        dict: Dictionary containing:
            - total_count (int): Total number of non-working days
            - details (list): List of dicts with date, type, and metadata
        
    Example:
        >>> from datetime import date
        >>> get_non_working_days_info(date(2026, 1, 24), date(2026, 1, 27))
        {
            'total_count': 2,
            'details': [
                {'date': '2026-01-25', 'type': 'weekend', 'day': 'Saturday'},
                {'date': '2026-01-26', 'type': 'holiday', 'name': 'Republic Day', 'description': '...'}
            ]
        }
    """
    if not start_date or not end_date:
        return {'total_count': 0, 'details': []}
    
    from apps.holidays.models import Holiday
    
    # Get all holidays in the date range
    holidays_query = Holiday.objects.filter(
        date__gte=start_date,
        date__lte=end_date,
        is_active=True,
        is_deleted=False
    )
    
    if region:
        holidays_query = holidays_query.filter(region=region)
    
    # Create a dict of holiday dates for quick lookup
    holidays_dict = {
        holiday.date: {
            'name': holiday.name,
            'description': holiday.description,
            'region': holiday.region or 'All India'
        }
        for holiday in holidays_query
    }
    
    non_working_days = []
    total_days = (end_date - start_date).days + 1
    
    for x in range(total_days):
        current_day = start_date + timedelta(days=x)
        
        # Check if it's a holiday
        if current_day in holidays_dict:
            holiday_info = holidays_dict[current_day]
            non_working_days.append({
                'date': str(current_day),
                'type': 'holiday',
                'name': holiday_info['name'],
                'description': holiday_info['description']
            })
        # Check if it's a weekend
        elif is_weekend(current_day):
            day_name = current_day.strftime('%A')  # 'Saturday' or 'Sunday'
            non_working_days.append({
                'date': str(current_day),
                'type': 'weekend',
                'day': day_name
            })
    
    return {
        'total_count': len(non_working_days),
        'details': non_working_days
    }


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