"""
Serializers for the session booking system.
"""

from rest_framework import serializers
from django.utils import timezone
from datetime import datetime, date, time

from .models import RecurrencePattern, SessionOccurrence


class RecurrencePatternSerializer(serializers.ModelSerializer):
    """Serializer for RecurrencePattern model."""
    
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
        read_only_fields = ['id', 'created_at', 'updated_at', 'weekday_name']
    
    def validate(self, data):
        """Validate pattern data."""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if end_date and start_date and start_date >= end_date:
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
    months_ahead = serializers.IntegerField(min_value=1, max_value=12, default=3)
    
    def validate(self, data):
        """Validate creation data."""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if end_date and start_date >= end_date:
            raise serializers.ValidationError({
                'end_date': 'End date must be after start date.'
            })
        
        return data


class SessionOccurrenceSerializer(serializers.ModelSerializer):
    """Serializer for SessionOccurrence model."""
    
    pattern_id = serializers.IntegerField(
        source='recurrence_pattern.id', 
        read_only=True,
        allow_null=True
    )
    is_one_time = serializers.BooleanField(read_only=True)
    is_recurring = serializers.BooleanField(read_only=True)
    end_datetime = serializers.DateTimeField(read_only=True)
    
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
        read_only_fields = [
            'id', 
            'created_at', 
            'updated_at',
            'pattern_id',
            'is_one_time',
            'is_recurring',
            'end_datetime',
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


class OccurrenceCancelSerializer(serializers.Serializer):
    """Serializer for cancelling an occurrence."""
    
    pass


class OccurrenceCompleteSerializer(serializers.Serializer):
    """Serializer for marking an occurrence as completed."""
    
    pass


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
