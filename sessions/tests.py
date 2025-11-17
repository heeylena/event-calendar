"""
Comprehensive tests for the refactored session booking system.

Tests cover:
- RecurrencePattern model and manager
- SessionOccurrence model and manager  
- Service layer (RecurrencePatternService, OccurrenceService, OccurrenceGenerationService)
- API endpoints (patterns and occurrences)
- Management commands
- Integration scenarios
"""

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import datetime, date, time, timedelta

from .models import RecurrencePattern, SessionOccurrence
from .services import (
    OccurrenceGenerationService,
    OccurrenceService,
    OccurrenceUpdateData,
    PatternUpdateData,
    RecurrencePatternService,
)


class RecurrencePatternModelTests(TestCase):
    """Test RecurrencePattern model and validation."""
    
    def test_create_recurrence_pattern(self):
        """Test creating a recurrence pattern."""
        pattern = RecurrencePattern.objects.create(
            title="Weekly Team Meeting",
            description="Every Monday at 10 AM",
            weekday=0,  # Monday
            time=time(10, 0),
            start_date=date(2024, 11, 4),
            duration_minutes=60
        )
        
        self.assertEqual(pattern.title, "Weekly Team Meeting")
        self.assertEqual(pattern.weekday, 0)
        self.assertEqual(pattern.weekday_name, "Monday")
        self.assertTrue(pattern.is_active)
    
    def test_pattern_with_end_date(self):
        """Test pattern with end date validation."""
        pattern = RecurrencePattern.objects.create(
            title="Limited Pattern",
            weekday=2,  # Wednesday
            time=time(14, 0),
            start_date=date(2024, 11, 1),
            end_date=date(2024, 12, 31),
            duration_minutes=90
        )
        
        self.assertEqual(pattern.end_date, date(2024, 12, 31))
    
    def test_pattern_end_date_validation(self):
        """Test that end_date must be after start_date."""
        with self.assertRaises(Exception):
            pattern = RecurrencePattern(
                title="Invalid Pattern",
                weekday=0,
                time=time(10, 0),
                start_date=date(2024, 12, 1),
                end_date=date(2024, 11, 1),  # Before start_date
                duration_minutes=60
            )
            pattern.full_clean()


class SessionOccurrenceModelTests(TestCase):
    """Test SessionOccurrence model."""
    
    def setUp(self):
        """Create a pattern for testing."""
        self.pattern = RecurrencePattern.objects.create(
            title="Test Pattern",
            weekday=0,
            time=time(10, 0),
            start_date=date(2024, 11, 4),
            duration_minutes=60
        )
    
    def test_create_recurring_occurrence(self):
        """Test creating an occurrence linked to a pattern."""
        occurrence = SessionOccurrence.objects.create(
            recurrence_pattern=self.pattern,
            title=self.pattern.title,
            start_datetime=timezone.make_aware(datetime(2024, 11, 4, 10, 0)),
            duration_minutes=60,
            status='scheduled'
        )
        
        self.assertFalse(occurrence.is_one_time)
        self.assertTrue(occurrence.is_recurring)
        self.assertEqual(occurrence.status, 'scheduled')
    
    def test_create_one_time_occurrence(self):
        """Test creating a one-time occurrence."""
        occurrence = SessionOccurrence.objects.create(
            recurrence_pattern=None,  # One-time
            title="One-time Meeting",
            start_datetime=timezone.make_aware(datetime(2024, 11, 15, 14, 0)),
            duration_minutes=90,
            status='scheduled'
        )
        
        self.assertTrue(occurrence.is_one_time)
        self.assertFalse(occurrence.is_recurring)
    
    def test_occurrence_end_datetime(self):
        """Test calculated end_datetime property."""
        occurrence = SessionOccurrence.objects.create(
            title="Test Meeting",
            start_datetime=timezone.make_aware(datetime(2024, 11, 15, 10, 0)),
            duration_minutes=90
        )
        
        expected_end = timezone.make_aware(datetime(2024, 11, 15, 11, 30))
        self.assertEqual(occurrence.end_datetime, expected_end)


class RecurrencePatternManagerTests(TestCase):
    """Test custom manager methods."""
    
    def setUp(self):
        """Create test patterns."""
        RecurrencePattern.objects.create(
            title="Active Monday",
            weekday=0,
            time=time(10, 0),
            start_date=date(2024, 11, 1),
            is_active=True
        )
        RecurrencePattern.objects.create(
            title="Inactive Tuesday",
            weekday=1,
            time=time(14, 0),
            start_date=date(2024, 11, 1),
            is_active=False
        )
        RecurrencePattern.objects.create(
            title="Active Wednesday",
            weekday=2,
            time=time(9, 0),
            start_date=date(2024, 11, 1),
            end_date=date(2024, 11, 30),
            is_active=True
        )
    
    def test_active_filter(self):
        """Test filtering active patterns."""
        active = RecurrencePattern.objects.active()
        self.assertEqual(active.count(), 2)
    
    def test_for_weekday_filter(self):
        """Test filtering by weekday."""
        monday_patterns = RecurrencePattern.objects.for_weekday(0)
        self.assertEqual(monday_patterns.count(), 1)
        self.assertEqual(monday_patterns.first().title, "Active Monday")
    
    def test_active_on_date(self):
        """Test filtering patterns active on specific date."""
        test_date = date(2024, 11, 15)
        active = RecurrencePattern.objects.active_on_date(test_date)
        self.assertEqual(active.count(), 2)
        
        # Test date after end_date
        future_date = date(2024, 12, 15)
        active_future = RecurrencePattern.objects.active_on_date(future_date)
        self.assertEqual(active_future.count(), 1)  # Only infinite one


class SessionOccurrenceManagerTests(TestCase):
    """Test SessionOccurrence custom manager."""
    
    def setUp(self):
        """Create test occurrences."""
        now = timezone.now()
        
        SessionOccurrence.objects.create(
            title="Past Scheduled",
            start_datetime=now - timedelta(days=5),
            status='scheduled'
        )
        SessionOccurrence.objects.create(
            title="Future Scheduled",
            start_datetime=now + timedelta(days=5),
            status='scheduled'
        )
        SessionOccurrence.objects.create(
            title="Cancelled",
            start_datetime=now + timedelta(days=3),
            status='cancelled'
        )
        SessionOccurrence.objects.create(
            title="Completed",
            start_datetime=now - timedelta(days=2),
            status='completed'
        )
    
    def test_scheduled_filter(self):
        """Test filtering scheduled occurrences."""
        scheduled = SessionOccurrence.objects.scheduled()
        self.assertEqual(scheduled.count(), 2)
    
    def test_upcoming_filter(self):
        """Test filtering upcoming occurrences."""
        upcoming = SessionOccurrence.objects.upcoming()
        self.assertEqual(upcoming.count(), 1)
        self.assertEqual(upcoming.first().title, "Future Scheduled")
    
    def test_past_filter(self):
        """Test filtering past occurrences."""
        past = SessionOccurrence.objects.past()
        self.assertEqual(past.count(), 2)
    
    def test_in_range_filter(self):
        """Test filtering by date range."""
        start = timezone.now() - timedelta(days=10)
        end = timezone.now() + timedelta(days=10)
        
        in_range = SessionOccurrence.objects.in_range(start, end)
        self.assertEqual(in_range.count(), 4)


class OccurrenceGenerationServiceTests(TestCase):
    """Test OccurrenceGenerationService."""
    
    def test_generate_for_pattern(self):
        """Test generating occurrences from a pattern."""
        pattern = RecurrencePattern.objects.create(
            title="Weekly Meeting",
            weekday=0,  # Monday
            time=time(10, 0),
            start_date=date(2024, 11, 4),
            duration_minutes=60
        )
        
        # Generate 1 month ahead
        occurrences = OccurrenceGenerationService.generate_for_pattern(
            pattern,
            months_ahead=1
        )
        
        # Should generate ~4 Mondays
        self.assertGreaterEqual(len(occurrences), 4)
        
        # Verify all are on Monday
        for occ in occurrences:
            self.assertEqual(occ.start_datetime.weekday(), 0)
    
    def test_no_duplicate_generation(self):
        """Test that re-running doesn't create duplicates."""
        pattern = RecurrencePattern.objects.create(
            title="Test Pattern",
            weekday=2,  # Wednesday
            time=time(14, 0),
            start_date=date(2024, 11, 1),
            duration_minutes=60
        )
        
        first_run = OccurrenceGenerationService.generate_for_pattern(pattern, months_ahead=1)
        first_count = len(first_run)
        
        second_run = OccurrenceGenerationService.generate_for_pattern(pattern, months_ahead=1)
        second_count = len(second_run)
        
        # Second run should create 0 new occurrences
        self.assertEqual(second_count, 0)
        
        # Total in DB should be first_count
        total = SessionOccurrence.objects.for_pattern(pattern).count()
        self.assertEqual(total, first_count)


class RecurrencePatternServiceTests(TestCase):
    """Test RecurrencePatternService."""
    
    def test_create_pattern_with_generation(self):
        """Test creating pattern and auto-generating occurrences."""
        pattern, count = RecurrencePatternService.create_pattern(
            title="New Meeting",
            weekday=3,  # Thursday
            time_of_day=time(15, 0),
            start_date=date(2024, 11, 1),
            duration_minutes=90,
            generate_occurrences=True,
            months_ahead=1
        )
        
        self.assertIsNotNone(pattern.id)
        self.assertGreater(count, 0)
        
        # Verify occurrences were created
        occurrences = SessionOccurrence.objects.for_pattern(pattern)
        self.assertEqual(occurrences.count(), count)
    
    def test_create_pattern_without_generation(self):
        """Test creating pattern without auto-generation."""
        pattern, count = RecurrencePatternService.create_pattern(
            title="Manual Pattern",
            weekday=4,
            time_of_day=time(11, 0),
            start_date=date(2024, 11, 1),
            generate_occurrences=False
        )
        
        self.assertIsNotNone(pattern.id)
        self.assertEqual(count, 0)


class OccurrenceServiceTests(TestCase):
    """Test OccurrenceService."""
    
    def setUp(self):
        """Create test data."""
        self.pattern = RecurrencePattern.objects.create(
            title="Test Pattern",
            weekday=0,
            time=time(10, 0),
            start_date=date(2024, 11, 4),
            duration_minutes=60
        )
        
        self.occ1 = SessionOccurrence.objects.create(
            recurrence_pattern=self.pattern,
            title="Meeting 1",
            start_datetime=timezone.make_aware(datetime(2024, 11, 4, 10, 0)),
            duration_minutes=60,
            status='scheduled'
        )
        self.occ2 = SessionOccurrence.objects.create(
            recurrence_pattern=self.pattern,
            title="Meeting 2",
            start_datetime=timezone.make_aware(datetime(2024, 11, 11, 10, 0)),
            duration_minutes=60,
            status='scheduled'
        )
    
    def test_get_occurrences_in_range(self):
        """Test getting occurrences in date range."""
        start = timezone.make_aware(datetime(2024, 11, 1, 0, 0))
        end = timezone.make_aware(datetime(2024, 11, 30, 23, 59))
        
        occurrences = OccurrenceService.get_occurrences_in_range(start, end)
        self.assertGreaterEqual(len(occurrences), 2)
    
    def test_create_one_time(self):
        """Test creating a one-time occurrence."""
        occurrence = OccurrenceService.create_one_time(
            title="Special Meeting",
            start_datetime=timezone.make_aware(datetime(2024, 11, 15, 14, 0)),
            duration_minutes=120,
            description="Important discussion"
        )
        
        self.assertTrue(occurrence.is_one_time)
        self.assertEqual(occurrence.duration_minutes, 120)
    
    def test_cancel_occurrence(self):
        """Test cancelling an occurrence."""
        OccurrenceService.cancel_occurrence(self.occ1)
        
        self.occ1.refresh_from_db()
        self.assertEqual(self.occ1.status, 'cancelled')
        self.assertTrue(self.occ1.is_exception)
    
    def test_complete_occurrence(self):
        """Test completing an occurrence."""
        OccurrenceService.complete_occurrence(self.occ1)
        
        self.occ1.refresh_from_db()
        self.assertEqual(self.occ1.status, 'completed')
    
    def test_update_occurrence(self):
        """Test updating an occurrence."""
        new_datetime = timezone.make_aware(datetime(2024, 11, 4, 11, 0))
        
        update_data = OccurrenceUpdateData(
            start_datetime=new_datetime,
            title="Updated Meeting"
        )
        updated = OccurrenceService.update_occurrence(
            self.occ1,
            update_data=update_data
        )
        
        self.assertEqual(updated.start_datetime, new_datetime)
        self.assertEqual(updated.title, "Updated Meeting")
        self.assertTrue(updated.is_exception)


class RecurrencePatternAPITests(APITestCase):
    """Test RecurrencePattern API endpoints."""
    
    def setUp(self):
        """Set up test client."""
        self.client = APIClient()
    
    def test_create_pattern(self):
        """Test creating a pattern via API."""
        data = {
            "title": "New Weekly Meeting",
            "description": "Team sync",
            "weekday": 1,  # Tuesday
            "time": "14:00:00",
            "start_date": "2024-11-05",
            "duration_minutes": 60,
            "generate_occurrences": False
        }
        
        response = self.client.post('/api/patterns/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('pattern', response.data)
        self.assertEqual(response.data['pattern']['title'], "New Weekly Meeting")
    
    def test_list_patterns(self):
        """Test listing patterns."""
        RecurrencePattern.objects.create(
            title="Pattern 1",
            weekday=0,
            time=time(10, 0),
            start_date=date(2024, 11, 1)
        )
        RecurrencePattern.objects.create(
            title="Pattern 2",
            weekday=2,
            time=time(14, 0),
            start_date=date(2024, 11, 1)
        )
        
        response = self.client.get('/api/patterns/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_get_pattern_detail(self):
        """Test retrieving a single pattern."""
        pattern = RecurrencePattern.objects.create(
            title="Test Pattern",
            weekday=3,
            time=time(9, 0),
            start_date=date(2024, 11, 1)
        )
        
        response = self.client.get(f'/api/patterns/{pattern.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], "Test Pattern")
    
    def test_update_pattern(self):
        """Test updating a pattern."""
        pattern = RecurrencePattern.objects.create(
            title="Original Title",
            weekday=0,
            time=time(10, 0),
            start_date=date(2024, 11, 1)
        )
        
        data = {"title": "Updated Title"}
        response = self.client.patch(f'/api/patterns/{pattern.id}/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], "Updated Title")
    
    def test_delete_pattern(self):
        """Test deleting a pattern."""
        pattern = RecurrencePattern.objects.create(
            title="To Delete",
            weekday=0,
            time=time(10, 0),
            start_date=date(2024, 11, 1)
        )
        
        response = self.client.delete(f'/api/patterns/{pattern.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(RecurrencePattern.objects.filter(id=pattern.id).exists())


class SessionOccurrenceAPITests(APITestCase):
    """Test SessionOccurrence API endpoints."""
    
    def setUp(self):
        """Set up test client and data."""
        self.client = APIClient()
        self.pattern = RecurrencePattern.objects.create(
            title="Test Pattern",
            weekday=0,
            time=time(10, 0),
            start_date=date(2024, 11, 4),
            duration_minutes=60
        )
        
        self.occurrence = SessionOccurrence.objects.create(
            recurrence_pattern=self.pattern,
            title="Test Occurrence",
            start_datetime=timezone.make_aware(datetime(2024, 11, 4, 10, 0)),
            duration_minutes=60,
            status='scheduled'
        )
    
    def test_create_one_time_occurrence(self):
        """Test creating a one-time occurrence."""
        data = {
            "title": "Special Event",
            "description": "One-time meeting",
            "start_datetime": "2024-11-15T14:00:00Z",
            "duration_minutes": 90
        }
        
        response = self.client.post('/api/occurrences/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], "Special Event")
    
    def test_list_occurrences_in_range(self):
        """Test listing occurrences with date range."""
        SessionOccurrence.objects.create(
            recurrence_pattern=self.pattern,
            title="Test Occurrence 2",
            start_datetime=timezone.make_aware(datetime(2024, 11, 11, 10, 0)),
            duration_minutes=60
        )
        
        response = self.client.get('/api/occurrences/', {
            'start': '2024-11-01T00:00:00Z',
            'end': '2024-11-30T23:59:59Z'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)
    
    def test_get_occurrence_detail(self):
        """Test retrieving a single occurrence."""
        response = self.client.get(f'/api/occurrences/{self.occurrence.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], "Test Occurrence")
    
    def test_update_occurrence(self):
        """Test updating an occurrence."""
        data = {
            "title": "Updated Occurrence",
            "start_datetime": "2024-11-04T11:00:00Z"
        }
        
        response = self.client.patch(
            f'/api/occurrences/{self.occurrence.id}/',
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], "Updated Occurrence")
    
    def test_cancel_occurrence(self):
        """Test cancelling an occurrence."""
        response = self.client.delete(f'/api/occurrences/{self.occurrence.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.occurrence.refresh_from_db()
        self.assertEqual(self.occurrence.status, 'cancelled')
    
    def test_complete_occurrence(self):
        """Test marking occurrence as completed."""
        response = self.client.post(f'/api/occurrences/{self.occurrence.id}/complete/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.occurrence.refresh_from_db()
        self.assertEqual(self.occurrence.status, 'completed')


class IntegrationTests(APITestCase):
    """End-to-end integration tests."""
    
    def setUp(self):
        """Set up test client."""
        self.client = APIClient()
    
    def test_complete_workflow(self):
        """Test complete workflow: create pattern, generate, modify, cancel."""
        pattern_data = {
            "title": "Weekly Team Sync",
            "weekday": 0,  # Monday
            "time": "10:00:00",
            "start_date": "2024-11-04",
            "duration_minutes": 60,
            "generate_occurrences": True,
            "months_ahead": 1
        }
        
        response = self.client.post('/api/patterns/', pattern_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        pattern_id = response.data['pattern']['id']
        occurrences_created = response.data['occurrences_created']
        self.assertGreater(occurrences_created, 0)
        
        response = self.client.get('/api/occurrences/', {
            'start': '2024-11-01T00:00:00Z',
            'end': '2024-11-30T23:59:59Z'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        nov_occurrences = response.data
        self.assertGreaterEqual(len(nov_occurrences), 4)  # 4 Mondays in Nov
        
        occurrence_to_cancel = nov_occurrences[2]  # Third Monday
        response = self.client.delete(f'/api/occurrences/{occurrence_to_cancel["id"]}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        

        response = self.client.get('/api/occurrences/', {
            'start': '2024-11-01T00:00:00Z',
            'end': '2024-11-30T23:59:59Z',
            'status': 'scheduled'
        })
        scheduled_only = response.data
        self.assertEqual(len(scheduled_only), len(nov_occurrences) - 1)
        
        occurrence_to_update = nov_occurrences[3]
        response = self.client.patch(
            f'/api/occurrences/{occurrence_to_update["id"]}/',
            {"start_datetime": "2024-11-25T11:00:00Z"},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_exception'])
        
        response = self.client.post('/api/occurrences/', {
            "title": "Quarterly Planning",
            "start_datetime": "2024-11-15T14:00:00Z",
            "duration_minutes": 120
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['is_one_time'])


class ManagementCommandTests(TestCase):
    """Test management commands."""
    
    def test_generate_occurrences_command(self):
        """Test the generate_occurrences management command."""
        from django.core.management import call_command
        from io import StringIO
        
        RecurrencePattern.objects.create(
            title="Test Pattern",
            weekday=0,
            time=time(10, 0),
            start_date=date(2024, 11, 4),
            duration_minutes=60
        )
        
        out = StringIO()
        call_command('generate_occurrences', '--months=2', stdout=out)
        
        output = out.getvalue()
        self.assertIn('Successfully generated', output)
        
        count = SessionOccurrence.objects.count()
        self.assertGreater(count, 0)
