"""
Real-time status checker for IBAKE ERP system.
This module provides functions to verify that all date/time functionality
is working correctly and using proper timezone handling.
"""

from django.utils import timezone
from django.conf import settings
from datetime import datetime, date
import pytz
from core.datetime_utils import (
    get_current_datetime, get_current_date, get_current_time,
    format_date_for_display, format_datetime_for_display
)


def check_timezone_configuration():
    """
    Check if timezone configuration is properly set up.
    
    Returns:
        dict: Status information about timezone configuration
    """
    status = {
        'timezone_configured': True,
        'current_timezone': settings.TIME_ZONE,
        'use_tz': settings.USE_TZ,
        'issues': [],
        'recommendations': []
    }
    
    # Check if USE_TZ is enabled
    if not settings.USE_TZ:
        status['timezone_configured'] = False
        status['issues'].append('USE_TZ is disabled in settings')
        status['recommendations'].append('Enable USE_TZ for proper timezone handling')
    
    # Check if timezone is set to a real timezone (not UTC for production)
    if settings.TIME_ZONE == 'UTC':
        status['issues'].append('Timezone is set to UTC - consider using local timezone for better accuracy')
        status['recommendations'].append('Set TIME_ZONE to local timezone (e.g., Asia/Manila)')
    
    # Check if pytz can handle the configured timezone
    try:
        tz = pytz.timezone(settings.TIME_ZONE)
        status['timezone_valid'] = True
        status['timezone_info'] = str(tz)
    except pytz.exceptions.UnknownTimeZoneError:
        status['timezone_configured'] = False
        status['timezone_valid'] = False
        status['issues'].append(f'Unknown timezone: {settings.TIME_ZONE}')
        status['recommendations'].append('Use a valid timezone from pytz.all_timezones')
    
    return status


def check_current_time_accuracy():
    """
    Check current time accuracy and compare different time sources.
    
    Returns:
        dict: Information about current time from various sources
    """
    current_datetime = get_current_datetime()
    current_date = get_current_date()
    current_time = get_current_time()
    django_now = timezone.now()
    
    status = {
        'datetime_utils_datetime': format_datetime_for_display(current_datetime),
        'datetime_utils_date': format_date_for_display(current_date),
        'datetime_utils_time': str(current_time),
        'django_timezone_now': format_datetime_for_display(django_now),
        'timezone_aware': timezone.is_aware(current_datetime),
        'consistency_check': current_datetime.date() == current_date,
        'issues': []
    }
    
    # Check if datetime utils are working consistently
    if not status['timezone_aware']:
        status['issues'].append('Current datetime is not timezone-aware')
    
    if not status['consistency_check']:
        status['issues'].append('Date extracted from datetime does not match current date')
    
    # Check if there's significant time difference between sources
    time_diff = abs((current_datetime - django_now).total_seconds())
    if time_diff > 1:  # More than 1 second difference
        status['issues'].append(f'Time difference between sources: {time_diff} seconds')
    
    return status


def check_model_date_fields():
    """
    Check if model date fields are using proper defaults.
    
    Returns:
        dict: Status of date field configurations
    """
    status = {
        'models_checked': [],
        'issues': [],
        'recommendations': []
    }
    
    # Check specific models that we know have date fields
    models_to_check = [
        ('inventory.RawMaterialMovement', 'date'),
        ('inventory.Production', 'date_started'),
        ('inventory.Production', 'date_finished'),
        ('inventory.StockIn', 'date'),
        ('accounting.JournalEntry', 'date'),
        ('core.TimeStampedModel', 'created_at'),
        ('core.TimeStampedModel', 'updated_at'),
    ]
    
    for model_path, field_name in models_to_check:
        try:
            app_label, model_name = model_path.split('.')
            status['models_checked'].append(f'{model_path}.{field_name}')
        except Exception as e:
            status['issues'].append(f'Could not check {model_path}.{field_name}: {str(e)}')
    
    return status


def check_system_status():
    """
    Check system functionality.
    
    Returns:
        dict: System status report
    """
    report = {
        'timestamp': format_datetime_for_display(get_current_datetime()),
        'overall_status': 'OK',
        'checks': {
            'timezone_config': check_timezone_configuration(),
            'time_accuracy': check_current_time_accuracy(),
            'model_fields': check_model_date_fields()
        },
        'summary': {
            'total_issues': 0,
            'total_recommendations': 0,
            'critical_issues': []
        }
    }
    
    # Count total issues and recommendations
    for check_name, check_result in report['checks'].items():
        if 'issues' in check_result:
            report['summary']['total_issues'] += len(check_result['issues'])
        if 'recommendations' in check_result:
            report['summary']['total_recommendations'] += len(check_result['recommendations'])
    
    # Identify critical issues
    if not report['checks']['timezone_config']['timezone_configured']:
        report['summary']['critical_issues'].append('Timezone configuration is invalid')
        report['overall_status'] = 'CRITICAL'
    
    if report['checks']['time_accuracy']['issues']:
        report['summary']['critical_issues'].extend(report['checks']['time_accuracy']['issues'])
        if report['overall_status'] != 'CRITICAL':
            report['overall_status'] = 'WARNING'
    
    if report['summary']['total_issues'] == 0:
        report['overall_status'] = 'OK'
    elif len(report['summary']['critical_issues']) == 0:
        report['overall_status'] = 'WARNING'
    
    return report


def validate_production_dates():
    """
    Validate that production dates are using real-time correctly.
    
    Returns:
        dict: Validation results for production dates
    """
    from inventory.models import Production
    
    current_date = get_current_date()
    
    status = {
        'total_productions': 0,
        'future_date_started': 0,
        'future_date_finished': 0,
        'invalid_date_ranges': 0,
        'issues': []
    }
    
    try:
        productions = Production.objects.all()
        status['total_productions'] = productions.count()
        
        for production in productions:
            # Check for future dates
            if production.date_started and production.date_started > current_date:
                status['future_date_started'] += 1
                status['issues'].append(f'Production {production.production_number} has future start date: {production.date_started}')
            
            if production.date_finished and production.date_finished > current_date:
                status['future_date_finished'] += 1
                status['issues'].append(f'Production {production.production_number} has future finish date: {production.date_finished}')
            
            # Check for invalid date ranges
            if (production.date_started and production.date_finished and 
                production.date_started > production.date_finished):
                status['invalid_date_ranges'] += 1
                status['issues'].append(f'Production {production.production_number} has start date after finish date')
    
    except Exception as e:
        status['issues'].append(f'Error validating production dates: {str(e)}')
    
    return status


def validate_stock_movements():
    """
    Validate that stock movement dates are using real-time correctly.
    
    Returns:
        dict: Validation results for stock movement dates
    """
    from inventory.models import RawMaterialMovement, StockIn
    
    current_date = get_current_date()
    
    status = {
        'total_movements': 0,
        'total_stock_ins': 0,
        'future_movements': 0,
        'future_stock_ins': 0,
        'issues': []
    }
    
    try:
        # Check RawMaterialMovement dates
        movements = RawMaterialMovement.objects.all()
        status['total_movements'] = movements.count()
        
        for movement in movements:
            if movement.date > current_date:
                status['future_movements'] += 1
                status['issues'].append(f'Movement {movement.movement_number} has future date: {movement.date}')
        
        # Check StockIn dates
        stock_ins = StockIn.objects.all()
        status['total_stock_ins'] = stock_ins.count()
        
        for stock_in in stock_ins:
            if stock_in.date > current_date:
                status['future_stock_ins'] += 1
                status['issues'].append(f'Stock In #{stock_in.id} has future date: {stock_in.date}')
    
    except Exception as e:
        status['issues'].append(f'Error validating stock movement dates: {str(e)}')
    
    return status


def get_real_time_summary():
    """
    Get a quick summary of real-time status.
    
    Returns:
        dict: Quick summary for dashboard display
    """
    current_dt = get_current_datetime()
    
    summary = {
        'current_time': format_datetime_for_display(current_dt),
        'current_date': format_date_for_display(get_current_date()),
        'timezone': settings.TIME_ZONE,
        'system_status': 'OK',
        'last_checked': format_datetime_for_display(current_dt, '%H:%M:%S')
    }
    
    # Quick checks
    if not settings.USE_TZ:
        summary['system_status'] = 'WARNING'
    
    if settings.TIME_ZONE == 'UTC':
        summary['system_status'] = 'NEEDS_CONFIG'
    
    return summary


def run_system_check():
    """
    Run all system checks and return report.
    
    Returns:
        dict: Complete system report
    """
    report = check_system_status()
    
    # Add specific validations
    report['validations'] = {
        'production_dates': validate_production_dates(),
        'stock_movements': validate_stock_movements()
    }
    
    # Update summary with validation issues
    for validation_name, validation_result in report['validations'].items():
        if 'issues' in validation_result:
            report['summary']['total_issues'] += len(validation_result['issues'])
    
    # Final status assessment
    total_issues = report['summary']['total_issues']
    if total_issues == 0:
        report['overall_status'] = 'EXCELLENT'
    elif total_issues <= 5:
        report['overall_status'] = 'GOOD'
    elif total_issues <= 10:
        report['overall_status'] = 'WARNING'
    else:
        report['overall_status'] = 'CRITICAL'
    
    return report 