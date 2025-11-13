"""
Comprehensive tests for the session booking system.

Coverage includes:
- Creating both session types
- Listing sessions with occurrence generation
- Updating single occurrences of recurring sessions
- Canceling single occurrences
- Edge cases and validation
"""

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import datetime, timedelta
from .models import Session, SessionException


class SessionModelTests(TestCase):
    """Test the Session model."""
    
    def test_create_one_time_session(self):
        """Test creating a one-time session."""
        session = Session.objects.create(
            title="Team Meeting",
            description="Weekly team sync",
            session_type="one_time",
            start_datetime=timezone.make_aware(datetime(2024, 11, 15, 10, 0)),
            duration_minutes=60
        )
        
        self.assertEqual(session.title, "Team Meeting")
        self.assertEqual(session.session_type, "one_time")
        self.assertIsNone(session.recurrence_day)
    
    def test_create_recurring_session(self):
        """Test creating a recurring session."""
        # Nov 4, 2024 is a Monday (weekday=0)
        session = Session.objects.create(
            title="Weekly Standup",
            description="Daily standup meeting",
            session_type="recurring",
            start_datetime=timezone.make_aware(datetime(2024, 11, 4, 10, 0)),
            duration_minutes=30,
            recurrence_day=0  # Monday
        )
        
        self.assertEqual(session.title, "Weekly Standup")
        self.assertEqual(session.session_type, "recurring")
        self.assertEqual(session.recurrence_day, 0)
    
    def test_recurring_session_validation_missing_day(self):
        """Test that recurring sessions require recurrence_day."""
        with self.assertRaises(Exception):
            Session.objects.create(
                title="Invalid Session",
                session_type="recurring",
                start_datetime=timezone.make_aware(datetime(2024, 11, 4, 10, 0)),
                duration_minutes=30
                # Missing recurrence_day
            )
    
    def test_recurring_session_validation_wrong_weekday(self):
        """Test that start_datetime must match recurrence_day."""
        # Nov 5, 2024 is a Tuesday (weekday=1), but we claim it's Monday
        with self.assertRaises(Exception):
            Session.objects.create(
                title="Invalid Session",
                session_type="recurring",
                start_datetime=timezone.make_aware(datetime(2024, 11, 5, 10, 0)),
                duration_minutes=30,
                recurrence_day=0  # Monday - but date is Tuesday
            )
    
    def test_one_time_session_occurrences(self):
        """Test generating occurrences for a one-time session."""
        session = Session.objects.create(
            title="One-time Event",
            session_type="one_time",
            start_datetime=timezone.make_aware(datetime(2024, 11, 15, 10, 0)),
            duration_minutes=60
        )
        
        # Get occurrences in range that includes the session
        start = timezone.make_aware(datetime(2024, 11, 1, 0, 0))
        end = timezone.make_aware(datetime(2024, 11, 30, 23, 59))
        occurrences = session.get_occurrences(start, end)
        
        self.assertEqual(len(occurrences), 1)
        self.assertEqual(occurrences[0]['title'], "One-time Event")
    
    def test_recurring_session_occurrences(self):
        """Test generating occurrences for a recurring session."""
        # Nov 4, 2024 is a Monday
        session = Session.objects.create(
            title="Weekly Meeting",
            session_type="recurring",
            start_datetime=timezone.make_aware(datetime(2024, 11, 4, 10, 0)),
            duration_minutes=60,
            recurrence_day=0  # Monday
        )
        
        # Get all Mondays in November 2024
        start = timezone.make_aware(datetime(2024, 11, 1, 0, 0))
        end = timezone.make_aware(datetime(2024, 11, 30, 23, 59))
        occurrences = session.get_occurrences(start, end)
        
        # November 2024 has 4 Mondays: 4, 11, 18, 25
        self.assertEqual(len(occurrences), 4)
        
        dates = [occ['occurrence_date'].day for occ in occurrences]
        self.assertEqual(dates, [4, 11, 18, 25])


class SessionExceptionTests(TestCase):
    """Test SessionException model and occurrence modifications."""
    
    def setUp(self):
        """Set up a recurring session for testing."""
        # Nov 4, 2024 is a Monday
        self.session = Session.objects.create(
            title="Weekly Meeting",
            session_type="recurring",
            start_datetime=timezone.make_aware(datetime(2024, 11, 4, 10, 0)),
            duration_minutes=60,
            recurrence_day=0  # Monday
        )
    
    def test_cancel_occurrence(self):
        """Test canceling a single occurrence."""
        # Cancel Nov 18
        exception = SessionException.objects.create(
            session=self.session,
            exception_date=datetime(2024, 11, 18).date(),
            is_cancelled=True
        )
        
        # Get occurrences for November
        start = timezone.make_aware(datetime(2024, 11, 1, 0, 0))
        end = timezone.make_aware(datetime(2024, 11, 30, 23, 59))
        occurrences = self.session.get_occurrences(start, end)
        
        # Should have 3 occurrences (Nov 18 is cancelled)
        self.assertEqual(len(occurrences), 3)
        dates = [occ['occurrence_date'].day for occ in occurrences]
        self.assertNotIn(18, dates)
        self.assertEqual(dates, [4, 11, 25])
    
    def test_modify_occurrence_datetime(self):
        """Test modifying the datetime of a single occurrence."""
        # Move Nov 25 from 10 AM to 11 AM
        exception = SessionException.objects.create(
            session=self.session,
            exception_date=datetime(2024, 11, 25).date(),
            is_cancelled=False,
            modified_datetime=timezone.make_aware(datetime(2024, 11, 25, 11, 0))
        )
        
        # Get occurrences for November
        start = timezone.make_aware(datetime(2024, 11, 1, 0, 0))
        end = timezone.make_aware(datetime(2024, 11, 30, 23, 59))
        occurrences = self.session.get_occurrences(start, end)
        
        # Should still have 4 occurrences
        self.assertEqual(len(occurrences), 4)
        
        # Find the Nov 25 occurrence
        nov_25 = next(occ for occ in occurrences if occ['occurrence_date'].day == 25)
        self.assertEqual(nov_25['datetime'].hour, 11)  # Modified to 11 AM
        self.assertTrue(nov_25['is_modified'])


class SessionAPITests(APITestCase):
    """Test the REST API endpoints."""
    
    def setUp(self):
        """Set up API client."""
        self.client = APIClient()
    
    def test_create_one_time_session(self):
        """Test creating a one-time session via API."""
        data = {
            'title': 'Project Review',
            'description': 'Q4 project review meeting',
            'session_type': 'one_time',
            'start_datetime': '2024-11-15T14:00:00Z',
            'duration_minutes': 90
        }
        
        response = self.client.post('/api/sessions/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Project Review')
        self.assertEqual(response.data['session_type'], 'one_time')
    
    def test_create_recurring_session(self):
        """Test creating a recurring session via API."""
        data = {
            'title': 'Monday Standup',
            'description': 'Weekly team standup',
            'session_type': 'recurring',
            'start_datetime': '2024-11-04T10:00:00Z',
            'duration_minutes': 30,
            'recurrence_day': 0  # Monday
        }
        
        response = self.client.post('/api/sessions/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Monday Standup')
        self.assertEqual(response.data['session_type'], 'recurring')
        self.assertEqual(response.data['recurrence_day'], 0)
    
    def test_create_recurring_session_wrong_weekday(self):
        """Test that API validates weekday matches start_datetime."""
        data = {
            'title': 'Invalid Session',
            'session_type': 'recurring',
            'start_datetime': '2024-11-05T10:00:00Z',  # Tuesday
            'duration_minutes': 30,
            'recurrence_day': 0  # Monday - mismatch!
        }
        
        response = self.client.post('/api/sessions/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_list_sessions_with_date_range(self):
        """Test listing sessions with date range generates occurrences."""
        # Create a recurring session
        Session.objects.create(
            title='Weekly Meeting',
            session_type='recurring',
            start_datetime=timezone.make_aware(datetime(2024, 11, 4, 10, 0)),
            duration_minutes=60,
            recurrence_day=0  # Monday
        )
        
        # Request occurrences for November 2024
        response = self.client.get(
            '/api/sessions/',
            {'start': '2024-11-01T00:00:00Z', 'end': '2024-11-30T23:59:59Z'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # November 2024 has 4 Mondays
        self.assertEqual(len(response.data), 4)
        
        # Verify they're sorted by datetime
        datetimes = [occ['datetime'] for occ in response.data]
        self.assertEqual(datetimes, sorted(datetimes))
    
    def test_list_sessions_without_date_range(self):
        """Test listing base sessions without date range."""
        # Create multiple sessions
        Session.objects.create(
            title='One-time Event',
            session_type='one_time',
            start_datetime=timezone.make_aware(datetime(2024, 11, 15, 10, 0)),
            duration_minutes=60
        )
        Session.objects.create(
            title='Weekly Meeting',
            session_type='recurring',
            start_datetime=timezone.make_aware(datetime(2024, 11, 4, 10, 0)),
            duration_minutes=60,
            recurrence_day=0
        )
        
        response = self.client.get('/api/sessions/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_retrieve_session(self):
        """Test retrieving a single session."""
        session = Session.objects.create(
            title='Team Retro',
            session_type='one_time',
            start_datetime=timezone.make_aware(datetime(2024, 11, 20, 15, 0)),
            duration_minutes=90
        )
        
        response = self.client.get(f'/api/sessions/{session.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Team Retro')
        self.assertEqual(response.data['duration_minutes'], 90)
    
    def test_update_session(self):
        """Test updating a session."""
        session = Session.objects.create(
            title='Original Title',
            session_type='one_time',
            start_datetime=timezone.make_aware(datetime(2024, 11, 20, 15, 0)),
            duration_minutes=60
        )
        
        response = self.client.patch(
            f'/api/sessions/{session.id}/',
            {'title': 'Updated Title', 'duration_minutes': 90},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Title')
        self.assertEqual(response.data['duration_minutes'], 90)
    
    def test_update_recurring_session_base(self):
        """Test that updating a recurring session updates the base template."""
        session = Session.objects.create(
            title='Weekly Standup',
            session_type='recurring',
            start_datetime=timezone.make_aware(datetime(2024, 11, 4, 10, 0)),
            duration_minutes=30,
            recurrence_day=0
        )
        
        # Update to start at 9 AM instead of 10 AM
        response = self.client.patch(
            f'/api/sessions/{session.id}/',
            {'start_datetime': '2024-11-04T09:00:00Z'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Get occurrences - should reflect new time
        response = self.client.get(
            '/api/sessions/',
            {'start': '2024-11-01T00:00:00Z', 'end': '2024-11-30T23:59:59Z'}
        )
        
        # All occurrences should be at 9 AM
        for occ in response.data:
            dt = datetime.fromisoformat(occ['datetime'].replace('Z', '+00:00'))
            self.assertEqual(dt.hour, 9)
    
    def test_delete_session(self):
        """Test deleting a session."""
        session = Session.objects.create(
            title='To Be Deleted',
            session_type='one_time',
            start_datetime=timezone.make_aware(datetime(2024, 11, 20, 15, 0)),
            duration_minutes=60
        )
        
        response = self.client.delete(f'/api/sessions/{session.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify it's deleted
        self.assertFalse(Session.objects.filter(id=session.id).exists())
    
    def test_cancel_single_occurrence(self):
        """Test canceling a single occurrence of a recurring session."""
        session = Session.objects.create(
            title='Weekly Meeting',
            session_type='recurring',
            start_datetime=timezone.make_aware(datetime(2024, 11, 4, 10, 0)),
            duration_minutes=60,
            recurrence_day=0
        )
        
        # Cancel Nov 18
        response = self.client.delete(f'/api/sessions/{session.id}/occurrences/2024-11-18/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify exception was created
        self.assertTrue(
            SessionException.objects.filter(
                session=session,
                exception_date=datetime(2024, 11, 18).date(),
                is_cancelled=True
            ).exists()
        )
        
        # Get occurrences - Nov 18 should be missing
        response = self.client.get(
            '/api/sessions/',
            {'start': '2024-11-01T00:00:00Z', 'end': '2024-11-30T23:59:59Z'}
        )
        
        self.assertEqual(len(response.data), 3)  # 3 instead of 4
        dates = [datetime.fromisoformat(occ['datetime'].replace('Z', '+00:00')).day 
                 for occ in response.data]
        self.assertNotIn(18, dates)
    
    def test_update_single_occurrence(self):
        """Test updating the datetime of a single occurrence."""
        session = Session.objects.create(
            title='Weekly Meeting',
            session_type='recurring',
            start_datetime=timezone.make_aware(datetime(2024, 11, 4, 10, 0)),
            duration_minutes=60,
            recurrence_day=0
        )
        
        # Move Nov 25 to 11 AM
        response = self.client.patch(
            f'/api/sessions/{session.id}/occurrences/2024-11-25/',
            {'new_datetime': '2024-11-25T11:00:00Z'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify exception was created
        exception = SessionException.objects.get(
            session=session,
            exception_date=datetime(2024, 11, 25).date()
        )
        self.assertFalse(exception.is_cancelled)
        self.assertEqual(exception.modified_datetime.hour, 11)
        
        # Get occurrences - Nov 25 should be at 11 AM
        response = self.client.get(
            '/api/sessions/',
            {'start': '2024-11-01T00:00:00Z', 'end': '2024-11-30T23:59:59Z'}
        )
        
        nov_25 = next(occ for occ in response.data 
                      if datetime.fromisoformat(occ['datetime'].replace('Z', '+00:00')).day == 25)
        dt = datetime.fromisoformat(nov_25['datetime'].replace('Z', '+00:00'))
        self.assertEqual(dt.hour, 11)
        self.assertTrue(nov_25['is_modified'])
    
    def test_update_occurrence_with_cancel_flag(self):
        """Test canceling an occurrence using PATCH with cancel flag."""
        session = Session.objects.create(
            title='Weekly Meeting',
            session_type='recurring',
            start_datetime=timezone.make_aware(datetime(2024, 11, 4, 10, 0)),
            duration_minutes=60,
            recurrence_day=0
        )
        
        response = self.client.patch(
            f'/api/sessions/{session.id}/occurrences/2024-11-18/',
            {'cancel': True},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify it's cancelled
        exception = SessionException.objects.get(
            session=session,
            exception_date=datetime(2024, 11, 18).date()
        )
        self.assertTrue(exception.is_cancelled)
    
    def test_invalid_occurrence_date_format(self):
        """Test that invalid date formats are rejected."""
        session = Session.objects.create(
            title='Weekly Meeting',
            session_type='recurring',
            start_datetime=timezone.make_aware(datetime(2024, 11, 4, 10, 0)),
            duration_minutes=60,
            recurrence_day=0
        )
        
        response = self.client.delete(f'/api/sessions/{session.id}/occurrences/invalid-date/')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_cancel_occurrence_wrong_weekday(self):
        """Test that canceling on wrong weekday is rejected."""
        session = Session.objects.create(
            title='Monday Meeting',
            session_type='recurring',
            start_datetime=timezone.make_aware(datetime(2024, 11, 4, 10, 0)),
            duration_minutes=60,
            recurrence_day=0  # Monday
        )
        
        # Try to cancel a Tuesday (Nov 5)
        response = self.client.delete(f'/api/sessions/{session.id}/occurrences/2024-11-05/')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('does not fall on the recurrence day', response.data['error'])
    
    def test_cancel_occurrence_before_start(self):
        """Test that canceling before session start is rejected."""
        session = Session.objects.create(
            title='Weekly Meeting',
            session_type='recurring',
            start_datetime=timezone.make_aware(datetime(2024, 11, 4, 10, 0)),
            duration_minutes=60,
            recurrence_day=0
        )
        
        # Try to cancel Oct 28 (before start date)
        response = self.client.delete(f'/api/sessions/{session.id}/occurrences/2024-10-28/')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class IntegrationTests(APITestCase):
    """Integration tests covering complete workflows."""
    
    def setUp(self):
        """Set up API client."""
        self.client = APIClient()
    
    def test_complete_recurring_session_workflow(self):
        """
        Test the complete workflow from the requirements:
        1. Create recurring Monday 10 AM session starting Nov 4, 2024
        2. List all sessions from Nov 1-30, 2024 (should show 4 Mondays)
        3. Cancel only the Nov 18 occurrence
        4. Update Nov 25 occurrence to 11 AM
        5. Update base recurring session time to 9 AM
        """
        
        # Step 1: Create recurring Monday session
        response = self.client.post('/api/sessions/', {
            'title': 'Monday Team Sync',
            'description': 'Weekly team synchronization',
            'session_type': 'recurring',
            'start_datetime': '2024-11-04T10:00:00Z',
            'duration_minutes': 60,
            'recurrence_day': 0
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session_id = response.data['id']
        
        # Step 2: List all sessions for November (should show 4 Mondays)
        response = self.client.get('/api/sessions/', {
            'start': '2024-11-01T00:00:00Z',
            'end': '2024-11-30T23:59:59Z'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)
        
        # Step 3: Cancel Nov 18 occurrence
        response = self.client.delete(f'/api/sessions/{session_id}/occurrences/2024-11-18/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify: List should now show 3 occurrences
        response = self.client.get('/api/sessions/', {
            'start': '2024-11-01T00:00:00Z',
            'end': '2024-11-30T23:59:59Z'
        })
        self.assertEqual(len(response.data), 3)
        
        # Step 4: Update Nov 25 occurrence to 11 AM
        response = self.client.patch(
            f'/api/sessions/{session_id}/occurrences/2024-11-25/',
            {'new_datetime': '2024-11-25T11:00:00Z'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify: Nov 25 should be at 11 AM
        response = self.client.get('/api/sessions/', {
            'start': '2024-11-01T00:00:00Z',
            'end': '2024-11-30T23:59:59Z'
        })
        nov_25 = next(occ for occ in response.data 
                      if datetime.fromisoformat(occ['datetime'].replace('Z', '+00:00')).day == 25)
        dt = datetime.fromisoformat(nov_25['datetime'].replace('Z', '+00:00'))
        self.assertEqual(dt.hour, 11)
        
        # Step 5: Update base session to 9 AM
        response = self.client.patch(
            f'/api/sessions/{session_id}/',
            {'start_datetime': '2024-11-04T09:00:00Z'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify: Future occurrences should be at 9 AM (except Nov 25 which remains at 11 AM)
        response = self.client.get('/api/sessions/', {
            'start': '2024-11-01T00:00:00Z',
            'end': '2024-12-31T23:59:59Z'
        })
        
        for occ in response.data:
            dt = datetime.fromisoformat(occ['datetime'].replace('Z', '+00:00'))
            if dt.day == 25 and dt.month == 11:
                # Nov 25 should still be at 11 AM (modified)
                self.assertEqual(dt.hour, 11)
            else:
                # All other occurrences should be at 9 AM
                self.assertEqual(dt.hour, 9)
