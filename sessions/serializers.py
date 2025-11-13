"""
Serializers for the session booking system.
"""

from rest_framework import serializers
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Session, SessionException


class SessionExceptionSerializer(serializers.ModelSerializer):
    """Serializer for session exceptions."""
    
    class Meta:
        model = SessionException
        fields = ['id', 'exception_date', 'is_cancelled', 'modified_datetime', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def validate(self, data):
        """Ensure exception is valid."""
        is_cancelled = data.get('is_cancelled', False)
        modified_datetime = data.get('modified_datetime')
        
        if is_cancelled and modified_datetime:
            raise serializers.ValidationError(
                "An exception cannot be both cancelled and have a modified datetime."
            )
        
        if not is_cancelled and not modified_datetime:
            raise serializers.ValidationError(
                "An exception must either be cancelled or have a modified datetime."
            )
        
        return data


class SessionSerializer(serializers.ModelSerializer):
    """
    Serializer for Session model.
    
    Handles both one-time and recurring sessions.
    """
    
    exceptions = SessionExceptionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Session
        fields = [
            'id',
            'title',
            'description',
            'session_type',
            'start_datetime',
            'duration_minutes',
            'recurrence_day',
            'exceptions',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate session data based on session type."""
        session_type = data.get('session_type')
        recurrence_day = data.get('recurrence_day')
        start_datetime = data.get('start_datetime')
        
        if session_type == 'recurring':
            if recurrence_day is None:
                raise serializers.ValidationError({
                    'recurrence_day': 'Recurrence day is required for recurring sessions.'
                })
            
            # Validate that start_datetime matches recurrence_day
            if start_datetime and start_datetime.weekday() != recurrence_day:
                weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                raise serializers.ValidationError({
                    'start_datetime': f'Start datetime must be on {weekday_names[recurrence_day]}.'
                })
        
        elif session_type == 'one_time':
            if recurrence_day is not None:
                raise serializers.ValidationError({
                    'recurrence_day': 'One-time sessions should not have a recurrence day.'
                })
        
        return data


class OccurrenceSerializer(serializers.Serializer):
    """
    Serializer for individual session occurrences.
    
    This is a read-only serializer used when listing sessions with their occurrences.
    """
    
    session_id = serializers.IntegerField()
    occurrence_date = serializers.DateField()
    datetime = serializers.DateTimeField()
    title = serializers.CharField()
    description = serializers.CharField()
    duration_minutes = serializers.IntegerField()
    is_modified = serializers.BooleanField()
    is_base_session = serializers.BooleanField(help_text="True if this is a one-time session")


class SessionListSerializer(serializers.Serializer):
    """
    Serializer for listing sessions with query parameters.
    
    Generates occurrences within the specified date range.
    """
    
    start = serializers.DateTimeField(required=True)
    end = serializers.DateTimeField(required=True)
    
    def validate(self, data):
        """Ensure start is before end."""
        if data['start'] >= data['end']:
            raise serializers.ValidationError("Start date must be before end date.")
        return data


class OccurrenceUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating a single occurrence of a recurring session.
    """
    
    new_datetime = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="New datetime for this occurrence (leave empty to cancel)"
    )
    cancel = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Set to true to cancel this occurrence"
    )
    
    def validate(self, data):
        """Ensure either cancel or new_datetime is provided, but not both."""
        new_datetime = data.get('new_datetime')
        cancel = data.get('cancel', False)
        
        if cancel and new_datetime:
            raise serializers.ValidationError(
                "Cannot both cancel and set a new datetime for an occurrence."
            )
        
        if not cancel and not new_datetime:
            raise serializers.ValidationError(
                "Must either cancel the occurrence or provide a new datetime."
            )
        
        return data


class SessionDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for a single session, including exceptions.
    """
    
    exceptions = SessionExceptionSerializer(many=True, read_only=True)
    weekday_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Session
        fields = [
            'id',
            'title',
            'description',
            'session_type',
            'start_datetime',
            'duration_minutes',
            'recurrence_day',
            'weekday_name',
            'exceptions',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'weekday_name']
    
    def get_weekday_name(self, obj):
        """Get human-readable weekday name for recurring sessions."""
        if obj.session_type == 'recurring' and obj.recurrence_day is not None:
            weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            return weekday_names[obj.recurrence_day]
        return None
