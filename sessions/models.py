"""
Models for the session booking system.

This implementation uses the Occurrence Materialization Pattern where:
- RecurrencePattern stores recurring session templates/rules
- SessionOccurrence stores ALL actual bookable session instances (both one-time and recurring)
"""

from datetime import timedelta

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from .managers import RecurrencePatternManager, SessionOccurrenceManager


class RecurrencePattern(models.Model):
    """
    Stores recurring session templates and rules.
    
    This model defines the pattern for recurring sessions (e.g., "Every Tuesday at 2pm").
    Actual occurrences are stored in SessionOccurrence model.
    """
    
    FREQUENCY_CHOICES = [
        ('weekly', 'Weekly'),
    ]
    
    WEEKDAY_CHOICES = [
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
    
    frequency = models.CharField(
        max_length=20, 
        choices=FREQUENCY_CHOICES,
        default='weekly'
    )
    weekday = models.IntegerField(
        choices=WEEKDAY_CHOICES,
        help_text="Day of week for recurring sessions (0=Monday, 6=Sunday)"
    )
    time = models.TimeField(help_text="Time of day for the session")
    duration_minutes = models.PositiveIntegerField(default=60)
    
    start_date = models.DateField(
        help_text="First date this pattern is active"
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Last date this pattern is active (null = no end date)"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this pattern is currently active"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = RecurrencePatternManager()
    
    class Meta:
        ordering = ['weekday', 'time']
        indexes = [
            models.Index(fields=['is_active', 'weekday']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        weekday_name = dict(self.WEEKDAY_CHOICES).get(self.weekday, 'Unknown')
        return f"{self.title} - Every {weekday_name} at {self.time.strftime('%H:%M')}"
    
    @property
    def weekday_name(self):
        """Get human-readable weekday name."""
        return dict(self.WEEKDAY_CHOICES).get(self.weekday, 'Unknown')
    
    def clean(self):
        """Validate pattern data."""
        super().clean()
        
        if self.end_date and self.start_date >= self.end_date:
            raise ValidationError({
                'end_date': 'End date must be after start date.'
            })
    
    def save(self, *args, **kwargs):
        """Save with validation."""
        self.full_clean()
        super().save(*args, **kwargs)


class SessionOccurrence(models.Model):
    """
    Stores ALL actual bookable session instances (both one-time and recurring).
    
    One-time sessions: recurrence_pattern = null
    Recurring sessions: reference their parent RecurrencePattern
    """
    
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    
    recurrence_pattern = models.ForeignKey(
        RecurrencePattern,
        on_delete=models.CASCADE,
        related_name='occurrences',
        null=True,
        blank=True,
        help_text="Parent pattern for recurring sessions (null for one-time sessions)"
    )
    
    start_datetime = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled'
    )
    is_exception = models.BooleanField(
        default=False,
        help_text="True if this occurrence was modified from its pattern"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = SessionOccurrenceManager()
    
    class Meta:
        ordering = ['start_datetime']
        indexes = [
            models.Index(fields=['start_datetime', 'status']),
            models.Index(fields=['recurrence_pattern', 'start_datetime']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        status_str = f" [{self.status}]" if self.status != 'scheduled' else ""
        return f"{self.title} - {self.start_datetime.strftime('%Y-%m-%d %H:%M')}{status_str}"
    
    @property
    def is_one_time(self):
        """Check if this is a one-time session."""
        return self.recurrence_pattern is None
    
    @property
    def is_recurring(self):
        """Check if this is part of a recurring pattern."""
        return self.recurrence_pattern is not None
    
    @property
    def end_datetime(self):
        """Calculate end datetime based on duration."""
        return self.start_datetime + timedelta(minutes=self.duration_minutes)
    
    def clean(self):
        """Validate occurrence data."""
        super().clean()
        
        if self.is_exception and not self.recurrence_pattern:
            raise ValidationError({
                'is_exception': 'One-time sessions cannot be marked as exceptions.'
            })
    
    def save(self, *args, **kwargs):
        """Save with validation."""
        self.full_clean()
        super().save(*args, **kwargs)
