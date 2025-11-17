"""
Service layer for session business logic.
Services are framework-agnostic and handle all business operations.
"""

from typing import List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from django.db import transaction
from django.utils import timezone

from .models import RecurrencePattern, SessionOccurrence


DAYS_PER_MONTH = 30


@dataclass
class PatternUpdateData:
    """DTO for pattern update operations."""
    title: Optional[str] = None
    description: Optional[str] = None
    time_of_day: Optional[time] = None
    duration_minutes: Optional[int] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None


@dataclass
class OccurrenceUpdateData:
    """DTO for occurrence update operations."""
    title: Optional[str] = None
    description: Optional[str] = None
    start_datetime: Optional[datetime] = None
    duration_minutes: Optional[int] = None


class OccurrenceGenerationService:
    """Service for generating occurrences from recurrence patterns."""
    
    @staticmethod
    def generate_for_pattern(
        pattern: RecurrencePattern,
        months_ahead: int = 3
    ) -> List[SessionOccurrence]:
        """
        Generate occurrences for a recurrence pattern.
        
        Args:
            pattern: RecurrencePattern instance
            months_ahead: How many months ahead to generate occurrences
            
        Returns:
            List of created SessionOccurrence instances
        """
        if not pattern.is_active:
            return []
        
        dates_to_generate = OccurrenceGenerationService._calculate_occurrence_dates(
            pattern, months_ahead
        )
        
        occurrences = OccurrenceGenerationService._create_occurrence_objects(
            pattern, dates_to_generate
        )
        
        return OccurrenceGenerationService._bulk_save_occurrences(occurrences)
    
    @staticmethod
    def _calculate_occurrence_dates(
        pattern: RecurrencePattern,
        months_ahead: int
    ) -> List[date]:
        """Calculate all dates on which occurrences should be generated."""
        end_date = OccurrenceGenerationService._get_end_generation_date(
            pattern, months_ahead
        )
        
        dates = []
        current_date = pattern.start_date
        
        while current_date <= end_date:
            if current_date.weekday() == pattern.weekday:
                dates.append(current_date)
            current_date += timedelta(days=1)
        
        return dates
    
    @staticmethod
    def _get_end_generation_date(pattern: RecurrencePattern, months_ahead: int) -> date:
        """Determine the end date for occurrence generation."""
        end_generation_date = timezone.now().date() + timedelta(
            days=DAYS_PER_MONTH * months_ahead
        )
        
        if pattern.end_date and pattern.end_date < end_generation_date:
            return pattern.end_date
        
        return end_generation_date
    
    @staticmethod
    def _create_occurrence_objects(
        pattern: RecurrencePattern,
        dates: List[date]
    ) -> List[SessionOccurrence]:
        """Create occurrence objects (not yet saved to DB)."""
        occurrences = []
        
        for occurrence_date in dates:
            if OccurrenceGenerationService._should_create_occurrence(pattern, occurrence_date):
                occurrence = SessionOccurrence(
                    recurrence_pattern=pattern,
                    title=pattern.title,
                    description=pattern.description,
                    start_datetime=OccurrenceGenerationService._make_aware_datetime(
                        occurrence_date, pattern.time
                    ),
                    duration_minutes=pattern.duration_minutes,
                    status='scheduled',
                    is_exception=False
                )
                occurrences.append(occurrence)
        
        return occurrences
    
    @staticmethod
    def _should_create_occurrence(pattern: RecurrencePattern, occurrence_date: date) -> bool:
        """Check if occurrence already exists for this date."""
        occurrence_datetime = OccurrenceGenerationService._make_aware_datetime(
            occurrence_date, pattern.time
        )
        
        return not SessionOccurrence.objects.filter(
            recurrence_pattern=pattern,
            start_datetime=occurrence_datetime
        ).exists()
    
    @staticmethod
    def _make_aware_datetime(date_obj: date, time_obj: time) -> datetime:
        """Combine date and time into timezone-aware datetime."""
        dt = datetime.combine(date_obj, time_obj)
        return timezone.make_aware(dt)
    
    @staticmethod
    def _bulk_save_occurrences(occurrences: List[SessionOccurrence]) -> List[SessionOccurrence]:
        """Bulk create occurrences in database."""
        if occurrences:
            SessionOccurrence.objects.bulk_create(occurrences)
        return occurrences
    
    @staticmethod
    def generate_for_all_patterns(months_ahead: int = 3) -> int:
        """
        Generate occurrences for all active patterns.
        
        Args:
            months_ahead: How many months ahead to generate occurrences
            
        Returns:
            Number of occurrences created
        """
        active_patterns = RecurrencePattern.objects.active()
        total_created = 0
        
        for pattern in active_patterns:
            created = OccurrenceGenerationService.generate_for_pattern(
                pattern, 
                months_ahead
            )
            total_created += len(created)
        
        return total_created


class OccurrenceService:
    """Service for managing individual session occurrences."""
    
    @staticmethod
    @transaction.atomic
    def create_one_time(
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
        OccurrenceService._validate_duration(duration_minutes)
        
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
    
    @staticmethod
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
            OccurrenceService._validate_duration(update_data.duration_minutes)
        
        if update_data.start_datetime:
            OccurrenceService._update_occurrence_datetime(occurrence, update_data.start_datetime)
        
        fields_to_update = {
            'title': update_data.title,
            'description': update_data.description,
            'duration_minutes': update_data.duration_minutes,
        }
        OccurrenceService._apply_field_updates(occurrence, fields_to_update)
        
        occurrence.save()
        return occurrence
    
    @staticmethod
    def _validate_duration(duration_minutes: int) -> None:
        """Validate duration is positive."""
        if duration_minutes <= 0:
            raise ValueError("Duration must be positive")
    
    @staticmethod
    def _update_occurrence_datetime(
        occurrence: SessionOccurrence,
        new_datetime: datetime
    ) -> None:
        """Update occurrence datetime and mark as exception if from pattern."""
        occurrence.start_datetime = new_datetime
        if occurrence.recurrence_pattern:
            occurrence.is_exception = True
    
    @staticmethod
    def _apply_field_updates(obj, fields: dict) -> None:
        """Apply field updates to object if values are not None (DRY helper)."""
        for field_name, value in fields.items():
            if value is not None:
                setattr(obj, field_name, value)
    
    @staticmethod
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
    
    @staticmethod
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
    
    @staticmethod
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


class RecurrencePatternService:
    """Service for managing recurrence patterns."""
    
    @staticmethod
    @transaction.atomic
    def create_pattern(
        title: str,
        weekday: int,
        time_of_day: time,
        start_date: date,
        duration_minutes: int = 60,
        description: str = '',
        end_date: Optional[date] = None,
        generate_occurrences: bool = True,
        months_ahead: int = 3
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
            months_ahead: How many months ahead to generate
            
        Returns:
            Tuple of (created RecurrencePattern, number of occurrences created)
            
        Raises:
            ValueError: If validation fails
        """
        RecurrencePatternService._validate_pattern_data(
            weekday, duration_minutes, start_date, end_date
        )
        
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
            created = OccurrenceGenerationService.generate_for_pattern(
                pattern, 
                months_ahead
            )
            occurrences_created = len(created)
        
        return pattern, occurrences_created
    
    @staticmethod
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
    
    @staticmethod
    @transaction.atomic
    def update_pattern(
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
        RecurrencePatternService._apply_field_updates(pattern, pattern_fields)
        pattern.save()
        
        if update_future_occurrences:
            RecurrencePatternService._update_future_occurrences(pattern, update_data)
        
        return pattern
    
    @staticmethod
    def _apply_field_updates(obj, fields: dict) -> None:
        """Apply field updates to object if values are not None (DRY helper)."""
        for field_name, value in fields.items():
            if value is not None:
                setattr(obj, field_name, value)
    
    @staticmethod
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
    
    @staticmethod
    @transaction.atomic
    def delete_pattern(
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
