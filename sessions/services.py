"""
Service layer for session business logic.
Services are framework-agnostic and handle all business operations.
"""

from typing import List, Optional, Tuple
from datetime import datetime, date, time, timedelta
from django.db import transaction
from django.utils import timezone

from .models import RecurrencePattern, SessionOccurrence
from .types import DEFAULT_DAYS_AHEAD, PatternUpdateData, OccurrenceUpdateData


def generate_occurrences_for_pattern(
    pattern: RecurrencePattern,
    days_ahead: int = DEFAULT_DAYS_AHEAD
) -> List[SessionOccurrence]:
    """
    Generate occurrences for a recurrence pattern.
    
    Args:
        pattern: RecurrencePattern instance
        days_ahead: How many days ahead to generate occurrences
        
    Returns:
        List of created SessionOccurrence instances
    """
    if not pattern.is_active:
        return []
    
    dates_to_generate = _calculate_occurrence_dates(pattern, days_ahead)
    occurrences = _create_occurrence_objects(pattern, dates_to_generate)
    return _bulk_save_occurrences(occurrences)


def generate_occurrences_for_all_patterns(days_ahead: int = DEFAULT_DAYS_AHEAD) -> int:
    """
    Generate occurrences for all active patterns.
    
    Args:
        days_ahead: How many days ahead to generate occurrences
        
    Returns:
        Number of occurrences created
    """
    active_patterns = RecurrencePattern.objects.active()
    total_created = 0
    
    for pattern in active_patterns:
        created = generate_occurrences_for_pattern(pattern, days_ahead)
        total_created += len(created)
    
    return total_created


def _calculate_occurrence_dates(
    pattern: RecurrencePattern,
    days_ahead: int
) -> List[date]:
    """Calculate all dates on which occurrences should be generated."""
    end_date = _get_end_generation_date(pattern, days_ahead)
    
    dates = []
    current_date = pattern.start_date
    
    days_until_target = (pattern.weekday - current_date.weekday()) % 7
    current_date += timedelta(days=days_until_target)
    
    while current_date <= end_date:
        dates.append(current_date)
        current_date += timedelta(days=7)
    
    return dates


def _get_end_generation_date(pattern: RecurrencePattern, days_ahead: int) -> date:
    """Determine the end date for occurrence generation."""
    end_generation_date = timezone.now().date() + timedelta(days=days_ahead)
    
    if pattern.end_date and pattern.end_date < end_generation_date:
        return pattern.end_date
    
    return end_generation_date


def _create_occurrence_objects(
    pattern: RecurrencePattern,
    dates: List[date]
) -> List[SessionOccurrence]:
    """Create occurrence objects (not yet saved to DB)."""
    datetimes_to_check = [_make_aware_datetime(d, pattern.time) for d in dates]
    existing_datetimes = set(
        SessionOccurrence.objects.filter(
            recurrence_pattern=pattern,
            start_datetime__in=datetimes_to_check
        ).values_list('start_datetime', flat=True)
    )
    
    occurrences = []
    for occurrence_date in dates:
        occurrence_datetime = _make_aware_datetime(occurrence_date, pattern.time)
        if occurrence_datetime not in existing_datetimes:
            occurrence = SessionOccurrence(
                recurrence_pattern=pattern,
                title=pattern.title,
                description=pattern.description,
                start_datetime=occurrence_datetime,
                duration_minutes=pattern.duration_minutes,
                status='scheduled',
                is_exception=False
            )
            occurrences.append(occurrence)
    
    return occurrences


def _make_aware_datetime(date_obj: date, time_obj: time) -> datetime:
    """Combine date and time into timezone-aware datetime."""
    dt = datetime.combine(date_obj, time_obj)
    return timezone.make_aware(dt)


def _bulk_save_occurrences(occurrences: List[SessionOccurrence]) -> List[SessionOccurrence]:
    """Bulk create occurrences in database."""
    if occurrences:
        SessionOccurrence.objects.bulk_create(occurrences)
    return occurrences


@transaction.atomic
def create_one_time_occurrence(
    title: str,
    start_datetime: datetime,
    duration_minutes: int = 60,
    description: str = ''
) -> SessionOccurrence:
    """
    Create a one-time session occurrence.
    
    Args:
        title: Session title
        start_datetime: When the session starts
        duration_minutes: Duration in minutes
        description: Session description
        
    Returns:
        Created SessionOccurrence instance
        
    Raises:
        ValueError: If duration_minutes is not positive
    """
    _validate_duration(duration_minutes)
    
    occurrence = SessionOccurrence.objects.create(
        recurrence_pattern=None,
        title=title,
        description=description,
        start_datetime=start_datetime,
        duration_minutes=duration_minutes,
        status='scheduled',
        is_exception=False
    )
    return occurrence


@transaction.atomic
def update_occurrence(
    occurrence: SessionOccurrence,
    update_data: OccurrenceUpdateData
) -> SessionOccurrence:
    """
    Update a session occurrence.
    
    Args:
        occurrence: SessionOccurrence instance to update
        update_data: OccurrenceUpdateData with fields to update
        
    Returns:
        Updated SessionOccurrence instance
        
    Raises:
        ValueError: If duration_minutes is not positive
    """
    if update_data.duration_minutes is not None:
        _validate_duration(update_data.duration_minutes)
    
    if update_data.start_datetime:
        _update_occurrence_datetime(occurrence, update_data.start_datetime)
    
    fields_to_update = {
        'title': update_data.title,
        'description': update_data.description,
        'duration_minutes': update_data.duration_minutes,
    }
    _apply_field_updates(occurrence, fields_to_update)
    
    occurrence.save()
    return occurrence


@transaction.atomic
def cancel_occurrence(occurrence: SessionOccurrence) -> SessionOccurrence:
    """
    Cancel a session occurrence.
    
    Args:
        occurrence: SessionOccurrence instance to cancel
        
    Returns:
        Updated SessionOccurrence instance
        
    Raises:
        ValueError: If occurrence is already cancelled
    """
    if occurrence.status == 'cancelled':
        raise ValueError("Occurrence is already cancelled")
    
    occurrence.status = 'cancelled'
    
    if occurrence.recurrence_pattern:
        occurrence.is_exception = True
    
    occurrence.save()
    return occurrence


@transaction.atomic
def complete_occurrence(occurrence: SessionOccurrence) -> SessionOccurrence:
    """
    Mark a session occurrence as completed.
    
    Args:
        occurrence: SessionOccurrence instance to complete
        
    Returns:
        Updated SessionOccurrence instance
        
    Raises:
        ValueError: If occurrence is already completed or cancelled
    """
    if occurrence.status == 'completed':
        raise ValueError("Occurrence is already completed")
    
    if occurrence.status == 'cancelled':
        raise ValueError("Cannot complete a cancelled occurrence")
    
    occurrence.status = 'completed'
    occurrence.save()
    return occurrence


def get_occurrences_in_range(
    start_datetime: datetime,
    end_datetime: datetime,
    status: Optional[str] = None
) -> List[SessionOccurrence]:
    """
    Get occurrences within a datetime range.
    
    Args:
        start_datetime: Range start
        end_datetime: Range end
        status: Optional status filter ('scheduled', 'cancelled', 'completed')
        
    Returns:
        List of SessionOccurrence instances
        
    Raises:
        ValueError: If start_datetime >= end_datetime
    """
    if start_datetime >= end_datetime:
        raise ValueError("Start datetime must be before end datetime")
    
    queryset = SessionOccurrence.objects.in_range(start_datetime, end_datetime)
    
    if status:
        queryset = queryset.filter(status=status)
    
    return list(queryset)


def _validate_duration(duration_minutes: int) -> None:
    """Validate duration is positive."""
    if duration_minutes <= 0:
        raise ValueError("Duration must be positive")


def _update_occurrence_datetime(
    occurrence: SessionOccurrence,
    new_datetime: datetime
) -> None:
    """Update occurrence datetime and mark as exception if from pattern."""
    occurrence.start_datetime = new_datetime
    if occurrence.recurrence_pattern:
        occurrence.is_exception = True


@transaction.atomic
def create_recurrence_pattern(
    title: str,
    weekday: int,
    time_of_day: time,
    start_date: date,
    duration_minutes: int = 60,
    description: str = '',
    end_date: Optional[date] = None,
    generate_occurrences: bool = True,
    days_ahead: int = DEFAULT_DAYS_AHEAD
) -> Tuple[RecurrencePattern, int]:
    """
    Create a new recurrence pattern and optionally generate occurrences.
    
    Args:
        title: Pattern title
        weekday: Day of week (0=Monday, 6=Sunday)
        time_of_day: Time of day for sessions
        start_date: First date pattern is active
        duration_minutes: Duration in minutes
        description: Pattern description
        end_date: Last date pattern is active (None = no end)
        generate_occurrences: Whether to generate occurrences immediately
        days_ahead: How many days ahead to generate occurrences
        
    Returns:
        Tuple of (created RecurrencePattern, number of occurrences created)
        
    Raises:
        ValueError: If validation fails
    """
    _validate_pattern_data(weekday, duration_minutes, start_date, end_date)
    
    pattern = RecurrencePattern.objects.create(
        title=title,
        description=description,
        frequency='weekly',
        weekday=weekday,
        time=time_of_day,
        duration_minutes=duration_minutes,
        start_date=start_date,
        end_date=end_date,
        is_active=True
    )
    
    occurrences_created = 0
    if generate_occurrences:
        created = generate_occurrences_for_pattern(pattern, days_ahead)
        occurrences_created = len(created)
    
    return pattern, occurrences_created


@transaction.atomic
def update_recurrence_pattern(
    pattern: RecurrencePattern,
    update_data: PatternUpdateData,
    update_future_occurrences: bool = True
) -> RecurrencePattern:
    """
    Update a recurrence pattern.
    
    Args:
        pattern: RecurrencePattern instance to update
        update_data: PatternUpdateData with fields to update
        update_future_occurrences: Whether to update future non-exception occurrences
        
    Returns:
        Updated RecurrencePattern instance
        
    Raises:
        ValueError: If validation fails
    """
    if update_data.duration_minutes is not None and update_data.duration_minutes <= 0:
        raise ValueError("Duration must be positive")
    
    pattern_fields = {
        'title': update_data.title,
        'description': update_data.description,
        'time': update_data.time_of_day,
        'duration_minutes': update_data.duration_minutes,
        'end_date': update_data.end_date,
        'is_active': update_data.is_active,
    }
    _apply_field_updates(pattern, pattern_fields)
    pattern.save()
    
    if update_future_occurrences:
        _update_future_occurrences(pattern, update_data)
    
    return pattern


@transaction.atomic
def delete_recurrence_pattern(
    pattern: RecurrencePattern,
    delete_future_occurrences: bool = True
) -> None:
    """
    Delete a recurrence pattern.
    
    Args:
        pattern: RecurrencePattern instance to delete
        delete_future_occurrences: If True, delete all future occurrences;
                                   If False, only deactivate the pattern
    """
    if delete_future_occurrences:
        SessionOccurrence.objects.filter(
            recurrence_pattern=pattern,
            start_datetime__gte=timezone.now()
        ).delete()
        pattern.delete()
    else:
        pattern.is_active = False
        pattern.save()


def _validate_pattern_data(
    weekday: int,
    duration_minutes: int,
    start_date: date,
    end_date: Optional[date]
) -> None:
    """Validate pattern creation data."""
    if not 0 <= weekday <= 6:
        raise ValueError("Weekday must be between 0 (Monday) and 6 (Sunday)")
    
    if duration_minutes <= 0:
        raise ValueError("Duration must be positive")
    
    if end_date and start_date >= end_date:
        raise ValueError("End date must be after start date")


def _update_future_occurrences(
    pattern: RecurrencePattern,
    update_data: PatternUpdateData
) -> None:
    """Update future non-exception occurrences."""
    future_occurrences = SessionOccurrence.objects.filter(
        recurrence_pattern=pattern,
        start_datetime__gte=timezone.now(),
        is_exception=False,
        status='scheduled'
    )
    
    updates = {}
    if update_data.title is not None:
        updates['title'] = update_data.title
    if update_data.description is not None:
        updates['description'] = update_data.description
    if update_data.duration_minutes is not None:
        updates['duration_minutes'] = update_data.duration_minutes
    
    if updates:
        future_occurrences.update(**updates)


def _apply_field_updates(obj, fields: dict) -> None:
    """Apply field updates to object if values are not None (DRY helper)."""
    for field_name, value in fields.items():
        if value is not None:
            setattr(obj, field_name, value)
