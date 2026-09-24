"""
Date and Time utilities for consistent real-time handling across the IBAKE ERP system.
This module ensures all date/time operations use proper timezone awareness and real-time accuracy.
"""

from django.utils import timezone
from datetime import datetime, date, time, timedelta
from django.conf import settings
import pytz


def get_current_datetime():
    """
    Get the current datetime in the application's timezone.
    Returns timezone-aware datetime object in local timezone.
    """
    utc_now = timezone.now()
    # Convert to local timezone
    local_tz = pytz.timezone(settings.TIME_ZONE)
    return utc_now.astimezone(local_tz)


def get_current_date():
    """
    Get the current date in the application's timezone.
    Returns date object in local timezone.
    """
    local_dt = get_current_datetime()
    return local_dt.date()


def get_current_time():
    """
    Get the current time in the application's timezone.
    Returns time object in local timezone.
    """
    local_dt = get_current_datetime()
    return local_dt.time()


def localize_datetime(dt):
    """
    Convert naive datetime to timezone-aware datetime.
    If already timezone-aware, returns as-is.
    
    Args:
        dt: datetime object (naive or aware)
    
    Returns:
        timezone-aware datetime object
    """
    if timezone.is_aware(dt):
        return dt
    
    # Get the timezone from settings
    tz = pytz.timezone(settings.TIME_ZONE)
    return tz.localize(dt)


def to_local_datetime(dt):
    """
    Convert timezone-aware datetime to local timezone.
    
    Args:
        dt: timezone-aware datetime object
    
    Returns:
        datetime object in local timezone
    """
    if not timezone.is_aware(dt):
        dt = localize_datetime(dt)
    
    # Convert to local timezone
    tz = pytz.timezone(settings.TIME_ZONE)
    return dt.astimezone(tz)


def format_date_for_display(date_obj, format_string='%Y-%m-%d'):
    """
    Format a date object for display purposes.
    
    Args:
        date_obj: date object
        format_string: strftime format string (default: ISO format)
    
    Returns:
        formatted date string
    """
    if date_obj is None:
        return ''
    
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    
    return date_obj.strftime(format_string)


def format_datetime_for_display(datetime_obj, format_string='%Y-%m-%d %H:%M:%S'):
    """
    Format a datetime object for display purposes.
    
    Args:
        datetime_obj: datetime object
        format_string: strftime format string
    
    Returns:
        formatted datetime string
    """
    if datetime_obj is None:
        return ''
    
    if not timezone.is_aware(datetime_obj):
        datetime_obj = localize_datetime(datetime_obj)
    
    # Convert to local timezone for display
    local_dt = to_local_datetime(datetime_obj)
    return local_dt.strftime(format_string)


def parse_date_input(date_string):
    """
    Parse date input from various formats to a date object.
    Enhanced with better error handling and real-time validation.
    
    Args:
        date_string: string representation of date
    
    Returns:
        date object or None if parsing fails
    """
    if not date_string:
        return None
    
    # Strip whitespace and normalize separators
    date_string = date_string.strip().replace('/', '-').replace('.', '-')
    
    # Common date formats to try
    date_formats = [
        '%Y-%m-%d',      # 2023-05-27 (ISO format - preferred)
        '%d-%m-%Y',      # 27-05-2023 (European format)
        '%m-%d-%Y',      # 05-27-2023 (US format)
        '%Y-%m-%d',      # 2023-5-27 (single digit)
        '%d-%m-%y',      # 27-05-23 (short year)
        '%m-%d-%y',      # 05-27-23 (US short year)
        '%Y%m%d',        # 20230527 (compact format)
        '%d%m%Y',        # 27052023 (compact European)
        '%m%d%Y',        # 05272023 (compact US)
    ]
    
    for fmt in date_formats:
        try:
            parsed_date = datetime.strptime(date_string, fmt).date()
            
            # Validate that the parsed date is reasonable (not too far in future/past)
            current_date = get_current_date()
            year_diff = abs(parsed_date.year - current_date.year)
            
            # Reject dates more than 100 years in the past or 10 years in the future
            if year_diff > 100 or (parsed_date > current_date and year_diff > 10):
                continue
                
            return parsed_date
        except ValueError:
            continue
    
    return None


def get_date_range_for_period(period='current_month'):
    """
    Get start and end dates for common time periods.
    
    Args:
        period: one of 'today', 'yesterday', 'current_week', 'current_month', 
                'current_year', 'last_month', 'last_year'
    
    Returns:
        tuple of (start_date, end_date)
    """
    today = get_current_date()
    
    if period == 'today':
        return today, today
    
    elif period == 'yesterday':
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    
    elif period == 'current_week':
        # Start of week (Monday)
        start_of_week = today - timedelta(days=today.weekday())
        return start_of_week, today
    
    elif period == 'current_month':
        start_of_month = today.replace(day=1)
        return start_of_month, today
    
    elif period == 'current_year':
        start_of_year = today.replace(month=1, day=1)
        return start_of_year, today
    
    elif period == 'last_month':
        # First day of last month
        first_of_this_month = today.replace(day=1)
        last_month_end = first_of_this_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        return last_month_start, last_month_end
    
    elif period == 'last_year':
        last_year = today.year - 1
        start_of_last_year = date(last_year, 1, 1)
        end_of_last_year = date(last_year, 12, 31)
        return start_of_last_year, end_of_last_year
    
    else:
        # Default to current month
        start_of_month = today.replace(day=1)
        return start_of_month, today


def is_business_day(check_date=None):
    """
    Check if a given date is a business day (Monday-Friday).
    
    Args:
        check_date: date object (defaults to current date)
    
    Returns:
        bool: True if business day, False if weekend
    """
    if check_date is None:
        check_date = get_current_date()
    
    return check_date.weekday() < 5  # Monday = 0, Sunday = 6


def add_business_days(start_date, business_days):
    """
    Add business days to a start date, skipping weekends.
    
    Args:
        start_date: date object
        business_days: number of business days to add
    
    Returns:
        date object
    """
    current_date = start_date
    days_added = 0
    
    while days_added < business_days:
        current_date += timedelta(days=1)
        if is_business_day(current_date):
            days_added += 1
    
    return current_date


def get_fiscal_year_dates(fiscal_year=None):
    """
    Get start and end dates for a fiscal year.
    Assumes fiscal year starts in January (can be customized).
    
    Args:
        fiscal_year: year (defaults to current year)
    
    Returns:
        tuple of (start_date, end_date)
    """
    if fiscal_year is None:
        fiscal_year = get_current_date().year
    
    start_date = date(fiscal_year, 1, 1)
    end_date = date(fiscal_year, 12, 31)
    
    return start_date, end_date


def calculate_age_in_days(start_date, end_date=None):
    """
    Calculate age/difference in days between two dates.
    
    Args:
        start_date: starting date
        end_date: ending date (defaults to current date)
    
    Returns:
        int: number of days
    """
    if end_date is None:
        end_date = get_current_date()
    
    return (end_date - start_date).days


def is_date_in_range(check_date, start_date, end_date):
    """
    Check if a date falls within a given range (inclusive).
    
    Args:
        check_date: date to check
        start_date: range start date
        end_date: range end date
    
    Returns:
        bool: True if date is in range
    """
    return start_date <= check_date <= end_date


def get_quarter_dates(year=None, quarter=None):
    """
    Get start and end dates for a specific quarter.
    
    Args:
        year: year (defaults to current year)
        quarter: quarter number 1-4 (defaults to current quarter)
    
    Returns:
        tuple of (start_date, end_date, quarter_name)
    """
    if year is None:
        year = get_current_date().year
    
    if quarter is None:
        current_month = get_current_date().month
        quarter = (current_month - 1) // 3 + 1
    
    quarter_starts = {
        1: (1, 1),   # Q1: Jan-Mar
        2: (4, 1),   # Q2: Apr-Jun
        3: (7, 1),   # Q3: Jul-Sep
        4: (10, 1),  # Q4: Oct-Dec
    }
    
    quarter_ends = {
        1: (3, 31),  # Q1: Jan-Mar
        2: (6, 30),  # Q2: Apr-Jun
        3: (9, 30),  # Q3: Jul-Sep
        4: (12, 31), # Q4: Oct-Dec
    }
    
    start_month, start_day = quarter_starts[quarter]
    end_month, end_day = quarter_ends[quarter]
    
    start_date = date(year, start_month, start_day)
    end_date = date(year, end_month, end_day)
    quarter_name = f"Q{quarter} {year}"
    
    return start_date, end_date, quarter_name


# Real-time validation functions
def validate_date_not_future(date_value, field_name="Date"):
    """
    Validate that a date is not in the future.
    
    Args:
        date_value: date to validate
        field_name: name of the field for error messages
    
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    if date_value is None:
        return True, ""
    
    current_date = get_current_date()
    if date_value > current_date:
        return False, f"{field_name} cannot be in the future. Current date is {format_date_for_display(current_date)}."
    
    return True, ""


def validate_date_range(start_date, end_date):
    """
    Validate that start_date is before or equal to end_date.
    
    Args:
        start_date: starting date
        end_date: ending date
    
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    if start_date is None or end_date is None:
        return True, ""
    
    if start_date > end_date:
        return False, "Start date cannot be after end date."
    
    return True, ""


def get_real_time_timestamp():
    """
    Get a real-time timestamp string for logging/audit purposes.
    
    Returns:
        str: formatted timestamp in UTC for consistency
    """
    # Use timezone.now() directly to avoid timezone conversion issues
    current_utc = timezone.now()
    # Format directly without converting to local timezone to maintain accuracy
    return current_utc.strftime('%Y-%m-%d %H:%M:%S.%f %Z')


def get_local_timestamp():
    """
    Get a real-time timestamp string in local timezone for display purposes.
    
    Returns:
        str: formatted timestamp in local timezone
    """
    return format_datetime_for_display(get_current_datetime(), '%Y-%m-%d %H:%M:%S')


def get_utc_now():
    """
    Get current UTC datetime for database consistency.
    
    Returns:
        timezone-aware datetime object in UTC
    """
    return timezone.now()


def ensure_timezone_consistency():
    """
    Verify that timezone configuration is consistent across the system.
    
    Returns:
        dict: Status information about timezone consistency
    """
    import time
    
    django_now = timezone.now()
    system_now = datetime.now()
    utc_now = datetime.utcnow()
    
    # Check if Django timezone is properly configured
    is_django_aware = timezone.is_aware(django_now)
    
    # Calculate timezone offsets
    django_offset = django_now.utcoffset().total_seconds() if django_now.utcoffset() else 0
    system_offset = time.timezone if time.daylight == 0 else time.altzone
    
    return {
        'django_timezone_aware': is_django_aware,
        'django_time': django_now.isoformat(),
        'system_time': system_now.isoformat(),
        'utc_time': utc_now.isoformat(),
        'django_offset_seconds': django_offset,
        'system_offset_seconds': -system_offset,  # time.timezone is negative of UTC offset
        'timezone_drift_seconds': abs(django_offset + system_offset),
        'configuration_valid': is_django_aware and abs(django_offset + system_offset) < 60
    }


def get_high_precision_timestamp():
    """
    Get a high-precision timestamp for critical operations.
    
    Returns:
        str: timestamp with microsecond precision
    """
    now = timezone.now()
    # Use UTC for consistency and avoid timezone conversion issues
    utc_now = now.utctimetuple()
    microseconds = now.microsecond
    
    return f"{now.strftime('%Y-%m-%d %H:%M:%S')}.{microseconds:06d} UTC"


def sync_check_datetime():
    """
    Perform a synchronization check between different datetime sources.
    
    Returns:
        dict: Synchronization status and timing information
    """
    import time
    from django.utils import timezone as django_tz
    
    # Capture multiple time sources simultaneously
    start_time = time.time()
    django_now = django_tz.now()
    python_now = datetime.now()
    utc_now = datetime.utcnow()
    end_time = time.time()
    
    # Calculate precision and drift
    capture_duration = (end_time - start_time) * 1000  # milliseconds
    
    return {
        'capture_duration_ms': capture_duration,
        'django_time': django_now.isoformat(),
        'python_local': python_now.isoformat(),
        'python_utc': utc_now.isoformat(),
        'timestamp_precision': 'microsecond' if capture_duration < 1 else 'second',
        'sync_status': 'good' if capture_duration < 10 else 'warning',
        'timezone_info': {
            'django_tz': str(django_now.tzinfo),
            'is_dst': time.daylight > 0,
            'timezone_name': time.tzname,
        }
    } 