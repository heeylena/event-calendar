"""
Serializers for the session booking system.
"""

from rest_framework import serializers
from django.utils import timezone
from datetime import datetime, date, time

from .models import RecurrencePattern, SessionOccurrence


class RecurrencePatternReadSerializer(serializers.ModelSerializer):
    """Serializer for reading/displaying RecurrencePattern (output)."""
    
    weekday_name = serializers.ReadOnlyField()
    
    class Meta:
        model = RecurrencePattern
        fields = [
            'id',
            'title',
            'description',
            'frequency',
            'weekday',
            'weekday_name',
            'time',
            'duration_minutes',
            'start_date',
            'end_date',
            'is_active',
            'created_at',
            'updated_at',
        ]


class RecurrencePatternWriteSerializer(serializers.ModelSerializer):
    """Serializer for updating RecurrencePattern (input)."""
    
    class Meta:
        model = RecurrencePattern
        fields = [
            'title',
            'description',
            'time',
            'duration_minutes',
            'end_date',
            'is_active',
        ]
    
    def validate(self, data):
        """Validate pattern data."""
        if 'end_date' in data and data['end_date']:
            start_date = self.instance.start_date if self.instance else None
            if start_date and data['end_date'] <= start_date:
                raise serializers.ValidationError({
                    'end_date': 'End date must be after start date.'
                })
        
        return data


class RecurrencePatternCreateSerializer(serializers.Serializer):
    """Serializer for creating a recurrence pattern with options."""
    
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    weekday = serializers.IntegerField(min_value=0, max_value=6)
    time = serializers.TimeField()
    duration_minutes = serializers.IntegerField(min_value=1, default=60)
    start_date = serializers.DateField()
    end_date = serializers.DateField(required=False, allow_null=True)
    generate_occurrences = serializers.BooleanField(default=True)
    days_ahead = serializers.IntegerField(min_value=1, max_value=90, default=7)
    
    def validate(self, data):
        """Validate creation data."""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if end_date and start_date >= end_date:
            raise serializers.ValidationError({
                'end_date': 'End date must be after start date.'
            })
        
        return data


class SessionOccurrenceReadSerializer(serializers.ModelSerializer):
    """Serializer for reading/displaying SessionOccurrence (output)."""
    
    pattern_id = serializers.IntegerField(
        source='recurrence_pattern.id', 
        allow_null=True
    )
    is_one_time = serializers.BooleanField()
    is_recurring = serializers.BooleanField()
    end_datetime = serializers.DateTimeField()
    
    class Meta:
        model = SessionOccurrence
        fields = [
            'id',
            'title',
            'description',
            'recurrence_pattern',
            'pattern_id',
            'start_datetime',
            'duration_minutes',
            'status',
            'is_exception',
            'is_one_time',
            'is_recurring',
            'end_datetime',
            'created_at',
            'updated_at',
        ]


class SessionOccurrenceCreateSerializer(serializers.Serializer):
    """Serializer for creating a one-time session occurrence."""
    
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    start_datetime = serializers.DateTimeField()
    duration_minutes = serializers.IntegerField(min_value=1, default=60)


class SessionOccurrenceUpdateSerializer(serializers.Serializer):
    """Serializer for updating a session occurrence."""
    
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    start_datetime = serializers.DateTimeField(required=False)
    duration_minutes = serializers.IntegerField(min_value=1, required=False)


class DateRangeQuerySerializer(serializers.Serializer):
    """Serializer for date range query parameters."""
    
    start = serializers.DateTimeField(required=True)
    end = serializers.DateTimeField(required=True)
    status = serializers.ChoiceField(
        choices=['scheduled', 'cancelled', 'completed'],
        required=False,
        allow_null=True
    )
    
    def validate(self, data):
        """Ensure start is before end."""
        if data['start'] >= data['end']:
            raise serializers.ValidationError(
                "Start datetime must be before end datetime."
            )
        return data


RecurrencePatternSerializer = RecurrencePatternReadSerializer
SessionOccurrenceSerializer = SessionOccurrenceReadSerializer
