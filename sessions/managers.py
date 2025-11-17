"""
Custom managers for session models.

Managers handle database query logic and filtering.
No business logic should be here - only query operations.
"""

from django.db import models
from django.utils import timezone
from datetime import datetime


class RecurrencePatternManager(models.Manager):
    """Custom manager for RecurrencePattern model."""
    
    def active(self):
        """Get all active recurrence patterns."""
        return self.filter(is_active=True)
    
    def for_weekday(self, weekday):
        """
        Get patterns for a specific weekday.
        
        Args:
            weekday: int (0=Monday, 6=Sunday)
        """
        return self.filter(weekday=weekday, is_active=True)
    
    def active_on_date(self, date):
        """
        Get patterns that are active on a specific date.
        
        Args:
            date: date object
        """
        return self.filter(
            is_active=True,
            start_date__lte=date
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=date)
        )


class SessionOccurrenceManager(models.Manager):
    """Custom manager for SessionOccurrence model."""
    
    def scheduled(self):
        """Get all scheduled (not cancelled/completed) occurrences."""
        return self.filter(status='scheduled')
    
    def upcoming(self):
        """Get upcoming scheduled occurrences."""
        return self.filter(
            status='scheduled',
            start_datetime__gte=timezone.now()
        )
    
    def past(self):
        """Get past occurrences."""
        return self.filter(start_datetime__lt=timezone.now())
    
    def in_range(self, start_datetime, end_datetime):
        """
        Get occurrences within a datetime range.
        
        Args:
            start_datetime: datetime object
            end_datetime: datetime object
        """
        return self.filter(
            start_datetime__gte=start_datetime,
            start_datetime__lte=end_datetime
        )
    
    def scheduled_in_range(self, start_datetime, end_datetime):
        """
        Get scheduled occurrences within a datetime range.
        
        Args:
            start_datetime: datetime object
            end_datetime: datetime object
        """
        return self.scheduled().in_range(start_datetime, end_datetime)
    
    def one_time(self):
        """Get one-time (non-recurring) occurrences."""
        return self.filter(recurrence_pattern__isnull=True)
    
    def recurring(self):
        """Get recurring occurrences."""
        return self.filter(recurrence_pattern__isnull=False)
    
    def for_pattern(self, pattern):
        """
        Get all occurrences for a specific recurrence pattern.
        
        Args:
            pattern: RecurrencePattern instance
        """
        return self.filter(recurrence_pattern=pattern)
    
    def exceptions(self):
        """Get occurrences that are exceptions (modified from pattern)."""
        return self.filter(is_exception=True)
