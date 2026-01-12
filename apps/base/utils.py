"""
Common utility functions used across the HRMS application.
"""
from datetime import timedelta, date


def calculate_working_days(start_date, end_date):
    """
    Calculate working days between two dates (excluding weekends).
    
    Args:
        start_date (date): Start date
        end_date (date): End date
        
    Returns:
        int: Number of working days (Monday-Friday)
        
    Example:
        >>> from datetime import date
        >>> calculate_working_days(date(2026, 2, 20), date(2026, 2, 23))
        2  # Friday and Monday (skips Sat/Sun)
    """
    if not start_date or not end_date:
        return 0
    
    total_days = (end_date - start_date).days + 1
    working_days = 0
    
    for x in range(total_days):
        current_day = start_date + timedelta(days=x)
        # weekday(): 0=Monday, 4=Friday, 5=Saturday, 6=Sunday
        if current_day.weekday() < 5:
            working_days += 1
            
    return working_days


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
