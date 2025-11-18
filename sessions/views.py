"""Views for the session booking system."""

from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import RecurrencePattern, SessionOccurrence
from .serializers import (
    RecurrencePatternReadSerializer,
    RecurrencePatternWriteSerializer,
    RecurrencePatternCreateSerializer,
    SessionOccurrenceReadSerializer,
    SessionOccurrenceCreateSerializer,
    SessionOccurrenceUpdateSerializer,
    DateRangeQuerySerializer,
)
from . import services
from .types import PatternUpdateData, OccurrenceUpdateData


class RecurrencePatternListCreateView(APIView):
    """
    List all recurrence patterns or create a new one.
    
    GET /api/patterns/ - List all patterns
    POST /api/patterns/ - Create a new pattern
    """
    
    def get(self, request):
        """List all recurrence patterns."""
        patterns = RecurrencePattern.objects.all()
        serializer = RecurrencePatternReadSerializer(patterns, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        """Create a new recurrence pattern with optional occurrence generation."""
        serializer = RecurrencePatternCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        pattern, occurrences_count = services.create_recurrence_pattern(
            title=data['title'],
            weekday=data['weekday'],
            time_of_day=data['time'],
            start_date=data['start_date'],
            duration_minutes=data.get('duration_minutes', 60),
            description=data.get('description', ''),
            end_date=data.get('end_date'),
            generate_occurrences=data.get('generate_occurrences', True),
            days_ahead=data.get('days_ahead', 7)
        )
        
        response_serializer = RecurrencePatternReadSerializer(pattern)
        return Response({
            'pattern': response_serializer.data,
            'occurrences_created': occurrences_count
        }, status=status.HTTP_201_CREATED)


class RecurrencePatternDetailView(APIView):
    """
    Retrieve, update, or delete a recurrence pattern.
    
    GET /api/patterns/{id}/ - Retrieve pattern
    PATCH /api/patterns/{id}/ - Update pattern
    DELETE /api/patterns/{id}/ - Delete pattern
    """
    
    def get(self, request, pk):
        """Retrieve a recurrence pattern."""
        pattern = get_object_or_404(RecurrencePattern, pk=pk)
        serializer = RecurrencePatternReadSerializer(pattern)
        return Response(serializer.data)
    
    def patch(self, request, pk):
        """Update a recurrence pattern."""
        pattern = get_object_or_404(RecurrencePattern, pk=pk)
        serializer = RecurrencePatternWriteSerializer(pattern, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        update_data = PatternUpdateData(
            title=serializer.validated_data.get('title'),
            description=serializer.validated_data.get('description'),
            time_of_day=serializer.validated_data.get('time'),
            duration_minutes=serializer.validated_data.get('duration_minutes'),
            end_date=serializer.validated_data.get('end_date'),
            is_active=serializer.validated_data.get('is_active')
        )
        updated_pattern = services.update_recurrence_pattern(
            pattern=pattern,
            update_data=update_data,
            update_future_occurrences=True
        )
        
        response_serializer = RecurrencePatternReadSerializer(updated_pattern)
        return Response(response_serializer.data)
    
    def delete(self, request, pk):
        """Delete a recurrence pattern."""
        pattern = get_object_or_404(RecurrencePattern, pk=pk)
        delete_future = request.query_params.get('delete_future', 'true').lower() == 'true'
        
        title = pattern.title
        services.delete_recurrence_pattern(pattern, delete_future_occurrences=delete_future)
        
        return Response({
            'message': f'Pattern "{title}" has been deleted.'
        }, status=status.HTTP_200_OK)


class SessionOccurrenceListView(APIView):
    """
    List occurrences within a date range or create a one-time occurrence.
    
    GET /api/occurrences/?start=X&end=Y - List occurrences in range
    POST /api/occurrences/ - Create a one-time occurrence
    """
    
    def get(self, request):
        """List occurrences within a date range."""
        query_serializer = DateRangeQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        
        start = query_serializer.validated_data['start']
        end = query_serializer.validated_data['end']
        status_filter = query_serializer.validated_data.get('status')
        
        occurrences = services.get_occurrences_in_range(
            start, 
            end, 
            status_filter
        )
        
        serializer = SessionOccurrenceReadSerializer(occurrences, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        """Create a one-time session occurrence."""
        serializer = SessionOccurrenceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        occurrence = services.create_one_time_occurrence(
            title=serializer.validated_data['title'],
            start_datetime=serializer.validated_data['start_datetime'],
            duration_minutes=serializer.validated_data.get('duration_minutes', 60),
            description=serializer.validated_data.get('description', '')
        )
        
        response_serializer = SessionOccurrenceReadSerializer(occurrence)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class SessionOccurrenceDetailView(APIView):
    """
    Retrieve, update, or delete a session occurrence.
    
    GET /api/occurrences/{id}/ - Retrieve occurrence
    PATCH /api/occurrences/{id}/ - Update occurrence
    DELETE /api/occurrences/{id}/ - Cancel occurrence
    """
    
    def get(self, request, pk):
        """Retrieve a session occurrence."""
        occurrence = get_object_or_404(SessionOccurrence, pk=pk)
        serializer = SessionOccurrenceReadSerializer(occurrence)
        return Response(serializer.data)
    
    def patch(self, request, pk):
        """Update a session occurrence."""
        occurrence = get_object_or_404(SessionOccurrence, pk=pk)
        serializer = SessionOccurrenceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        update_data = OccurrenceUpdateData(
            start_datetime=serializer.validated_data.get('start_datetime'),
            title=serializer.validated_data.get('title'),
            description=serializer.validated_data.get('description'),
            duration_minutes=serializer.validated_data.get('duration_minutes')
        )
        updated_occurrence = services.update_occurrence(
            occurrence=occurrence,
            update_data=update_data
        )
        
        response_serializer = SessionOccurrenceReadSerializer(updated_occurrence)
        return Response(response_serializer.data)
    
    def delete(self, request, pk):
        """Cancel a session occurrence."""
        occurrence = get_object_or_404(SessionOccurrence, pk=pk)
        
        services.cancel_occurrence(occurrence)
        
        return Response({
            'message': f'Occurrence "{occurrence.title}" on {occurrence.start_datetime.date()} has been cancelled.'
        }, status=status.HTTP_200_OK)


class OccurrenceCompleteView(APIView):
    """
    Mark a session occurrence as completed.
    
    POST /api/occurrences/{id}/complete/
    """
    
    def post(self, request, pk):
        """Mark occurrence as completed."""
        occurrence = get_object_or_404(SessionOccurrence, pk=pk)
        
        services.complete_occurrence(occurrence)
        
        return Response({
            'message': f'Occurrence "{occurrence.title}" has been marked as completed.'
        }, status=status.HTTP_200_OK)
