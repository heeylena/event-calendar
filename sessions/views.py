"""
Views for the session booking system.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime, parse_date
from datetime import datetime, timedelta

from .models import Session, SessionException
from .serializers import (
    SessionSerializer,
    SessionDetailSerializer,
    OccurrenceSerializer,
    OccurrenceUpdateSerializer,
)


class SessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing sessions.
    
    Endpoints:
    - POST /api/sessions/ - Create a new session
    - GET /api/sessions/ - List sessions (with ?start=X&end=Y for occurrences)
    - GET /api/sessions/{id}/ - Retrieve session details
    - PATCH /api/sessions/{id}/ - Update session
    - DELETE /api/sessions/{id}/ - Delete session
    - PATCH /api/sessions/{id}/occurrences/{date}/ - Update single occurrence
    - DELETE /api/sessions/{id}/occurrences/{date}/ - Cancel single occurrence
    """
    
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    
    def get_serializer_class(self):
        """Use detailed serializer for retrieve action."""
        if self.action == 'retrieve':
            return SessionDetailSerializer
        return SessionSerializer
    
    def list(self, request, *args, **kwargs):
        """
        List sessions with optional date range filtering.
        
        Query Parameters:
        - start: Start datetime (ISO format, required for occurrences)
        - end: End datetime (ISO format, required for occurrences)
        
        If start and end are provided, returns all occurrences within the range.
        Otherwise, returns the base sessions.
        """
        start_param = request.query_params.get('start')
        end_param = request.query_params.get('end')
        
        # If date range is provided, generate occurrences
        if start_param and end_param:
            try:
                start_dt = parse_datetime(start_param)
                end_dt = parse_datetime(end_param)
                
                if not start_dt or not end_dt:
                    return Response(
                        {'error': 'Invalid datetime format. Use ISO 8601 format (e.g., 2024-11-01T00:00:00Z)'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                if start_dt >= end_dt:
                    return Response(
                        {'error': 'Start datetime must be before end datetime.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Get all sessions
                sessions = Session.objects.all()
                
                # Generate occurrences for each session
                all_occurrences = []
                for session in sessions:
                    occurrences = session.get_occurrences(start_dt, end_dt)
                    all_occurrences.extend(occurrences)
                
                # Sort by datetime
                all_occurrences.sort(key=lambda x: x['datetime'])
                
                serializer = OccurrenceSerializer(all_occurrences, many=True)
                return Response(serializer.data)
                
            except Exception as e:
                return Response(
                    {'error': f'Error processing date range: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # No date range: return base sessions
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """Create a new session."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Return with detailed serializer
        instance = serializer.instance
        detail_serializer = SessionDetailSerializer(instance)
        
        return Response(
            detail_serializer.data,
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        """
        Update a session.
        
        For recurring sessions, this updates the base template.
        All future occurrences (without exceptions) will reflect the changes.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Return with detailed serializer
        detail_serializer = SessionDetailSerializer(instance)
        return Response(detail_serializer.data)
    
    @action(detail=True, methods=['patch', 'delete'], url_path='occurrences/(?P<occurrence_date>[^/.]+)')
    def manage_occurrence(self, request, pk=None, occurrence_date=None):
        """
        Manage a single occurrence of a session.
        
        PATCH: Update the datetime of a specific occurrence
        DELETE: Cancel a specific occurrence
        
        URL: /api/sessions/{id}/occurrences/{date}/
        
        For PATCH, provide:
        {
            "new_datetime": "2024-11-19T11:00:00Z"  // New datetime for this occurrence
        }
        
        For DELETE, no body is needed.
        """
        session = self.get_object()
        
        # Parse the occurrence date
        try:
            occ_date = parse_date(occurrence_date)
            if not occ_date:
                return Response(
                    {'error': 'Invalid date format. Use YYYY-MM-DD format.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD format.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # For one-time sessions, only allow operations on the exact date
        if session.session_type == 'one_time':
            if occ_date != session.start_datetime.date():
                return Response(
                    {'error': 'Cannot modify occurrence: this is a one-time session on a different date.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # For recurring sessions, verify the date falls on the correct weekday
        if session.session_type == 'recurring':
            if occ_date.weekday() != session.recurrence_day:
                return Response(
                    {'error': f'The date {occ_date} does not fall on the recurrence day for this session.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Verify the date is not before the session starts
            if occ_date < session.start_datetime.date():
                return Response(
                    {'error': 'Cannot modify occurrence before the session start date.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if request.method == 'DELETE':
            # Cancel this occurrence
            exception, created = SessionException.objects.update_or_create(
                session=session,
                exception_date=occ_date,
                defaults={
                    'is_cancelled': True,
                    'modified_datetime': None,
                }
            )
            
            return Response(
                {'message': f'Occurrence on {occ_date} has been cancelled.'},
                status=status.HTTP_200_OK
            )
        
        elif request.method == 'PATCH':
            # Update this occurrence
            serializer = OccurrenceUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            new_datetime = serializer.validated_data.get('new_datetime')
            cancel = serializer.validated_data.get('cancel', False)
            
            if cancel:
                # Cancel this occurrence
                exception, created = SessionException.objects.update_or_create(
                    session=session,
                    exception_date=occ_date,
                    defaults={
                        'is_cancelled': True,
                        'modified_datetime': None,
                    }
                )
                return Response(
                    {'message': f'Occurrence on {occ_date} has been cancelled.'},
                    status=status.HTTP_200_OK
                )
            
            elif new_datetime:
                # Modify this occurrence
                exception, created = SessionException.objects.update_or_create(
                    session=session,
                    exception_date=occ_date,
                    defaults={
                        'is_cancelled': False,
                        'modified_datetime': new_datetime,
                    }
                )
                return Response(
                    {
                        'message': f'Occurrence on {occ_date} has been moved to {new_datetime}.',
                        'new_datetime': new_datetime,
                    },
                    status=status.HTTP_200_OK
                )
        
        return Response(
            {'error': 'Invalid request method.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a session.
        
        This will delete the session and all its exceptions.
        """
        instance = self.get_object()
        session_type = instance.session_type
        title = instance.title
        
        self.perform_destroy(instance)
        
        return Response(
            {'message': f'{session_type.replace("_", " ").title()} session "{title}" has been deleted.'},
            status=status.HTTP_200_OK
        )
