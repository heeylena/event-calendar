"""
Models for the session booking system.

Design Decision: Exception-Based Approach
=========================================
For recurring sessions, we use an exception-based model where:
- The Session model stores the base pattern (recurring rules)
- The SessionException model stores deviations (cancellations or modifications)

Benefits:
- Storage efficient: Don't store thousands of future occurrences
- Flexible: Easy to update all future occurrences of a recurring session
- Scalable: Works well for long-running or "infinite" recurring sessions
- Clean: Exceptions are explicit and auditable

Trade-offs:
- Slightly more complex query logic to generate occurrences
- Need to check exceptions when rendering occurrences
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta


class Session(models.Model):
    """
    Represents a session (one-time or recurring).
    
    For one-time sessions:
        - session_type = 'one_time'
        - start_datetime is the exact datetime
        - recurrence_day is None
        
    For recurring sessions:
        - session_type = 'recurring'
        - start_datetime is the first occurrence datetime
        - recurrence_day is the weekday (0=Monday, 6=Sunday)
    """
    
    SESSION_TYPES = [
        ('one_time', 'One-time Session'),
        ('recurring', 'Recurring Weekly Session'),
    ]
    
    WEEKDAYS = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    session_type = models.CharField(max_length=20, choices=SESSION_TYPES)
    start_datetime = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    
    # Recurring session fields
    recurrence_day = models.IntegerField(
        choices=WEEKDAYS,
        null=True,
        blank=True,
        help_text="Day of week for recurring sessions (0=Monday, 6=Sunday)"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['start_datetime']
        indexes = [
            models.Index(fields=['session_type', 'start_datetime']),
            models.Index(fields=['recurrence_day']),
        ]
    
    def __str__(self):
        if self.session_type == 'one_time':
            return f"{self.title} - {self.start_datetime.strftime('%Y-%m-%d %H:%M')}"
        else:
            day_name = dict(self.WEEKDAYS).get(self.recurrence_day, 'Unknown')
            return f"{self.title} - Every {day_name} at {self.start_datetime.strftime('%H:%M')}"
    
    def clean(self):
        """Validate session data."""
        super().clean()
        
        if self.session_type == 'recurring':
            if self.recurrence_day is None:
                raise ValidationError({
                    'recurrence_day': 'Recurrence day is required for recurring sessions.'
                })
            # Verify that start_datetime matches the recurrence_day
            if self.start_datetime and self.start_datetime.weekday() != self.recurrence_day:
                raise ValidationError({
                    'start_datetime': f'Start datetime must be on the specified recurrence day ({dict(self.WEEKDAYS)[self.recurrence_day]}).'
                })
        elif self.session_type == 'one_time':
            if self.recurrence_day is not None:
                raise ValidationError({
                    'recurrence_day': 'One-time sessions should not have a recurrence day.'
                })
    
    def save(self, *args, **kwargs):
        """Save with validation."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def get_occurrences(self, start_date, end_date):
        """
        Generate all occurrences of this session within the date range.
        
        Args:
            start_date: datetime object for range start
            end_date: datetime object for range end
            
        Returns:
            List of dicts with occurrence information
        """
        occurrences = []
        
        if self.session_type == 'one_time':
            # Simple case: single occurrence
            if start_date <= self.start_datetime <= end_date:
                exception = self.exceptions.filter(
                    exception_date=self.start_datetime.date()
                ).first()
                
                if exception and exception.is_cancelled:
                    return []  # This occurrence is cancelled
                
                occurrence_data = {
                    'session_id': self.id,
                    'occurrence_date': self.start_datetime.date(),
                    'datetime': exception.modified_datetime if exception else self.start_datetime,
                    'title': self.title,
                    'description': self.description,
                    'duration_minutes': self.duration_minutes,
                    'is_modified': exception is not None and not exception.is_cancelled,
                    'is_base_session': True,
                }
                occurrences.append(occurrence_data)
        
        else:  # recurring
            # Generate occurrences for each week in the range
            current = self.start_datetime
            
            # Fast-forward to the first occurrence in range if start_date is after start_datetime
            if start_date > current:
                days_diff = (start_date - current).days
                weeks_diff = days_diff // 7
                current = current + timedelta(weeks=weeks_diff)
                # Make sure we're at or after start_date
                while current < start_date:
                    current += timedelta(weeks=1)
            
            while current <= end_date:
                occurrence_date = current.date()
                
                # Check if this occurrence has an exception
                exception = self.exceptions.filter(
                    exception_date=occurrence_date
                ).first()
                
                if exception and exception.is_cancelled:
                    # Skip cancelled occurrences
                    current += timedelta(weeks=1)
                    continue
                
                occurrence_data = {
                    'session_id': self.id,
                    'occurrence_date': occurrence_date,
                    'datetime': exception.modified_datetime if exception else current,
                    'title': self.title,
                    'description': self.description,
                    'duration_minutes': self.duration_minutes,
                    'is_modified': exception is not None,
                    'is_base_session': False,
                }
                occurrences.append(occurrence_data)
                
                # Move to next week
                current += timedelta(weeks=1)
        
        return occurrences


class SessionException(models.Model):
    """
    Represents an exception to a recurring session (or one-time session modification).
    
    Used to:
    - Cancel a specific occurrence of a recurring session
    - Modify the datetime of a specific occurrence
    """
    
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='exceptions'
    )
    exception_date = models.DateField(
        help_text="The date of the occurrence being modified/cancelled"
    )
    is_cancelled = models.BooleanField(
        default=False,
        help_text="If True, this occurrence is cancelled"
    )
    modified_datetime = models.DateTimeField(
        null=True,
        blank=True,
        help_text="If set, this occurrence is moved to this datetime"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['session', 'exception_date']
        ordering = ['exception_date']
        indexes = [
            models.Index(fields=['session', 'exception_date']),
        ]
    
    def __str__(self):
        if self.is_cancelled:
            return f"Cancelled: {self.session.title} on {self.exception_date}"
        elif self.modified_datetime:
            return f"Modified: {self.session.title} on {self.exception_date} -> {self.modified_datetime}"
        return f"Exception for {self.session.title} on {self.exception_date}"
    
    def clean(self):
        """Validate exception data."""
        super().clean()
        
        if self.is_cancelled and self.modified_datetime:
            raise ValidationError(
                "An exception cannot be both cancelled and have a modified datetime."
            )
        
        if not self.is_cancelled and not self.modified_datetime:
            raise ValidationError(
                "An exception must either be cancelled or have a modified datetime."
            )
    
    def save(self, *args, **kwargs):
        """Save with validation."""
        self.full_clean()
        super().save(*args, **kwargs)
