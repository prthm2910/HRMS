"""
Common utility functions used across the HRMS application.
"""
from datetime import timedelta
import threading
import calendar

_thread_locals = threading.local()


def get_month_name(month: int) -> str:
    """
    Convert month number to month name
    
    Args:
        month (int): Month number (1-12)
        
    Returns:
        str: Full month name (e.g., 'January', 'February')
        
    Example:
        >>> get_month_name(1)
        'January'
        >>> get_month_name(12)
        'December'
    """
    if not 1 <= month <= 12:
        raise ValueError(f"Month must be between 1 and 12, got {month}")
    
    return calendar.month_name[month]



def calculate_working_and_non_working_days(start_date, end_date, region=None):
    """
    Calculate working and non-working days (weekends and holidays) between two dates.
    
    Args:
        start_date (date/datetime): Start date
        end_date (date/datetime): End date
        region (str, optional): Region to filter holidays
        
    Returns:
        dict: {
            'working_days': int,
            'non_working_days': int,
            'weekend_count': int,
            'holiday_count': int,
            'total_days': int,
            'details': list,
            'holidays': list
        }
    """
    if not start_date or not end_date:
        return {
            'working_days': 0,
            'non_working_days': 0,
            'weekend_count': 0,
            'holiday_count': 0,
            'total_days': 0,
            'details': [],
            'holidays': []
        }
    
    # Handle datetime inputs by extracting the date part
    if hasattr(start_date, 'date'):
        start_date = start_date.date()
    if hasattr(end_date, 'date'):
        end_date = end_date.date()
    
    if start_date > end_date:
        return {
            'working_days': 0,
            'non_working_days': 0,
            'weekend_count': 0,
            'holiday_count': 0,
            'total_days': 0,
            'details': [],
            'holidays': []
        }

    # Import here to avoid circular imports
    from apps.holidays.models import Holiday
    
    # Get active holidays in the date range
    holidays_query = Holiday.objects.filter(
        holiday_date__date__gte=start_date,
        holiday_date__date__lte=end_date,
        is_active=True,
        is_deleted=False
    )
    
    if region:
        holidays_query = holidays_query.filter(region=region)
    
    # Map holidays for quick lookup
    holidays_dict = {
        h.holiday_date.date(): {
            'name': h.name,
            'region': h.region or 'All'
        } for h in holidays_query
    }
    
    total_days = (end_date - start_date).days + 1
    working_days = 0
    weekend_count = 0
    holiday_count = 0
    details = []
    holidays_list = []

    for x in range(total_days):
        current_day = start_date + timedelta(days=x)
        day_info = {
            'date': str(current_day),
            'is_working': True,
            'reason': None
        }
        
        # Check holiday first (holidays take precedence over weekends in some policies, 
        # but here we identify them separately)
        if current_day in holidays_dict:
            h_info = holidays_dict[current_day]
            day_info['is_working'] = False
            day_info['reason'] = 'Holiday'
            day_info['holiday_name'] = h_info['name']
            holiday_count += 1
            holidays_list.append({
                'date': str(current_day),
                'name': h_info['name'],
                'region': h_info['region']
            })
        # Check weekend
        elif current_day.weekday() >= 5:  # 5=Saturday, 6=Sunday
            day_info['is_working'] = False
            day_info['reason'] = 'Weekend'
            day_info['day_name'] = current_day.strftime('%A')
            weekend_count += 1
        else:
            working_days += 1
            
        details.append(day_info)
        
    return {
        'working_days': working_days,
        'non_working_days': weekend_count + holiday_count,
        'weekend_count': weekend_count,
        'holiday_count': holiday_count,
        'total_days': total_days,
        'details': details,
        'holidays': holidays_list
    }


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
            holiday_date__date=check_date,
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


# Function and logic merged into calculate_working_and_non_working_days
pass


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