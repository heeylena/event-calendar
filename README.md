# Event Calendar Backend - Django REST API

A production-ready REST API for session booking with support for one-time and recurring weekly sessions.

## Table of Contents
- [Design Decisions](#design-decisions)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Running the Project](#running-the-project)
- [API Documentation](#api-documentation)
- [Postman Collection](#postman-collection)
- [Testing](#testing)
- [Project Structure](#project-structure)

---

## Design Decisions

### Exception-Based Approach for Recurring Sessions

This project uses an **exception-based model** for handling recurring sessions:

#### Architecture
- **Session Model**: Stores the base pattern for recurring sessions (e.g., "Every Monday at 10 AM")
- **SessionException Model**: Stores deviations from the pattern (cancellations or time modifications)

#### Benefits
1. **Storage Efficiency**: No need to store thousands of future occurrences in the database
2. **Flexibility**: Easy to update all future occurrences by modifying the base session
3. **Scalability**: Works well for long-running or "infinite" recurring sessions
4. **Auditability**: Exceptions are explicit and easily tracked
5. **Performance**: Occurrence generation happens on-demand during queries

#### Trade-offs
- Slightly more complex query logic to generate occurrences
- Need to check for exceptions when rendering each occurrence

#### Alternative Considered
**Instance-based approach** (storing each occurrence as a separate database row) was considered but rejected because:
- Would require pre-generating occurrences (how many? until when?)
- Updating a recurring session would require updating potentially hundreds of rows
- More storage overhead
- Complicated handling of "infinite" recurring sessions

---

## Features

✅ **Session Types**
- One-time sessions (single occurrence)
- Recurring weekly sessions (repeat on the same weekday)

✅ **CRUD Operations**
- Create, read, update, and delete sessions
- List sessions with occurrence generation for date ranges

✅ **Occurrence Management**
- Cancel specific occurrences of recurring sessions
- Modify the datetime of specific occurrences
- Update base recurring session (affects all future non-modified occurrences)

✅ **Validation**
- Ensures recurring sessions match their specified weekday
- Prevents invalid date operations
- Comprehensive error messages

✅ **No Authentication**
- Single global user (as per requirements)
- Focus on core functionality

---

## Requirements

- Python 3.10+
- Django 4.2+
- Django REST Framework 3.14+
- Docker & Docker Compose (for PostgreSQL database)

---

## Installation

### Option 1: Quick Setup with Docker (Recommended)

**Automated setup with PostgreSQL in Docker:**

```bash
# Make script executable
chmod +x setup-docker.sh

# Run setup (starts Docker, creates venv, installs deps, runs migrations)
./setup-docker.sh
```

This will:
- ✅ Start PostgreSQL in Docker
- ✅ Create virtual environment
- ✅ Install all dependencies
- ✅ Run migrations
- ✅ Run tests to verify setup

**See `DOCKER_SETUP.md` for detailed Docker documentation.**

---

### Option 2: Manual Setup with Docker

1. **Clone the repository**
```bash
git clone <repository-url>
cd event-calendar
```

2. **Copy environment file**
```bash
cp .env.example .env
```

3. **Start PostgreSQL database**
```bash
docker-compose up -d
```

4. **Create and activate a virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

5. **Install dependencies**
```bash
pip install -r requirements.txt
```

6. **Run migrations**
```bash
python manage.py makemigrations
python manage.py migrate
```

7. **Create a superuser (optional, for admin access)**
```bash
python manage.py createsuperuser
```

---

### Option 3: SQLite (No Docker)

For quick testing without Docker:

1. **Update `.env` file:**
```env
DB_ENGINE=sqlite
```

2. **Follow steps 4-7 from Option 2**

No Docker needed - uses SQLite database file.

---

## Running the Project

1. **Start the development server**
```bash
python manage.py runserver
```

2. **Access the API**
- API Root: http://localhost:8000/api/
- Django Admin: http://localhost:8000/admin/
- Browsable API: http://localhost:8000/api/sessions/

---

## API Documentation

### Base URL
```
http://localhost:8000/api/
```

### Endpoints

#### 1. Create Session
**POST** `/api/sessions/`

**One-time Session Example:**
```bash
curl -X POST http://localhost:8000/api/sessions/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Project Review",
    "description": "Q4 project review meeting",
    "session_type": "one_time",
    "start_datetime": "2024-11-15T14:00:00Z",
    "duration_minutes": 90
  }'
```

**Recurring Session Example:**
```bash
curl -X POST http://localhost:8000/api/sessions/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Monday Team Sync",
    "description": "Weekly team synchronization",
    "session_type": "recurring",
    "start_datetime": "2024-11-04T10:00:00Z",
    "duration_minutes": 60,
    "recurrence_day": 0
  }'
```

**Recurrence Day Values:**
- 0 = Monday
- 1 = Tuesday
- 2 = Wednesday
- 3 = Thursday
- 4 = Friday
- 5 = Saturday
- 6 = Sunday

---

#### 2. List Sessions
**GET** `/api/sessions/`

**Without date range** (returns base sessions):
```bash
curl http://localhost:8000/api/sessions/
```

**With date range** (returns all occurrences):
```bash
curl "http://localhost:8000/api/sessions/?start=2024-11-01T00:00:00Z&end=2024-11-30T23:59:59Z"
```

**Response Example:**
```json
[
  {
    "session_id": 1,
    "occurrence_date": "2024-11-04",
    "datetime": "2024-11-04T10:00:00Z",
    "title": "Monday Team Sync",
    "description": "Weekly team synchronization",
    "duration_minutes": 60,
    "is_modified": false,
    "is_base_session": false
  },
  {
    "session_id": 1,
    "occurrence_date": "2024-11-11",
    "datetime": "2024-11-11T10:00:00Z",
    "title": "Monday Team Sync",
    "description": "Weekly team synchronization",
    "duration_minutes": 60,
    "is_modified": false,
    "is_base_session": false
  }
]
```

---

#### 3. Retrieve Session Details
**GET** `/api/sessions/{id}/`

```bash
curl http://localhost:8000/api/sessions/1/
```

**Response Example:**
```json
{
  "id": 1,
  "title": "Monday Team Sync",
  "description": "Weekly team synchronization",
  "session_type": "recurring",
  "start_datetime": "2024-11-04T10:00:00Z",
  "duration_minutes": 60,
  "recurrence_day": 0,
  "weekday_name": "Monday",
  "exceptions": [
    {
      "id": 1,
      "exception_date": "2024-11-18",
      "is_cancelled": true,
      "modified_datetime": null,
      "created_at": "2024-11-13T10:30:00Z"
    }
  ],
  "created_at": "2024-11-13T10:00:00Z",
  "updated_at": "2024-11-13T10:00:00Z"
}
```

---

#### 4. Update Session
**PATCH** `/api/sessions/{id}/`

Updates the base session. For recurring sessions, this affects all future occurrences (except those with exceptions).

```bash
curl -X PATCH http://localhost:8000/api/sessions/1/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Monday Morning Sync",
    "start_datetime": "2024-11-04T09:00:00Z"
  }'
```

---

#### 5. Delete Session
**DELETE** `/api/sessions/{id}/`

```bash
curl -X DELETE http://localhost:8000/api/sessions/1/
```

---

#### 6. Cancel Single Occurrence
**DELETE** `/api/sessions/{id}/occurrences/{date}/`

Cancels a specific occurrence of a recurring session.

```bash
curl -X DELETE http://localhost:8000/api/sessions/1/occurrences/2024-11-18/
```

---

#### 7. Update Single Occurrence
**PATCH** `/api/sessions/{id}/occurrences/{date}/`

Modifies the datetime of a specific occurrence.

**Move to a new time:**
```bash
curl -X PATCH http://localhost:8000/api/sessions/1/occurrences/2024-11-25/ \
  -H "Content-Type: application/json" \
  -d '{
    "new_datetime": "2024-11-25T11:00:00Z"
  }'
```

**Cancel using PATCH:**
```bash
curl -X PATCH http://localhost:8000/api/sessions/1/occurrences/2024-11-25/ \
  -H "Content-Type: application/json" \
  -d '{
    "cancel": true
  }'
```

---

## Postman Collection

A complete Postman collection is included for easy API testing and demonstration.

### Import Collection

1. Open Postman
2. Click **Import**
3. Select `Event_Calendar_API.postman_collection.json`
4. The collection will appear with 15 pre-configured requests

### Collection Contents

The collection includes:
- ✅ Creating one-time and recurring sessions
- ✅ Listing sessions with date range filtering
- ✅ Canceling single occurrences
- ✅ Modifying single occurrences
- ✅ Updating base sessions
- ✅ Error handling examples
- ✅ Complete demo workflow (numbered 1-10)

### Quick Demo Flow

**For interviews or presentations, run these requests in order:**

1. **Create Recurring Session** → Monday 10 AM starting Nov 4
2. **List November Occurrences** → Shows 4 Mondays
3. **Cancel Nov 18** → Remove one occurrence
4. **List Again** → Shows 3 Mondays
5. **Modify Nov 25 to 11 AM** → Change single occurrence
6. **Update Base to 9 AM** → Affects all future
7. **List December** → Shows new time
8. **Verify Nov 25** → Still at 11 AM (exception preserved)

**See `POSTMAN_DEMO_GUIDE.md` for detailed presentation tips and talking points.**

**See `DEMO_CHEATSHEET.md` for a quick reference during demos.**

---

## Testing

### Run All Tests
```bash
python manage.py test sessions
```

### Run Specific Test Classes
```bash
# Model tests
python manage.py test sessions.tests.SessionModelTests

# API tests
python manage.py test sessions.tests.SessionAPITests

# Integration tests
python manage.py test sessions.tests.IntegrationTests
```

### Run with Coverage
```bash
# Install coverage
pip install coverage

# Run tests with coverage
coverage run --source='.' manage.py test sessions
coverage report
coverage html  # Generate HTML report
```

### Test Coverage
The test suite includes:
- ✅ Creating one-time and recurring sessions
- ✅ Validating session data
- ✅ Generating occurrences for date ranges
- ✅ Canceling single occurrences
- ✅ Modifying single occurrences
- ✅ Updating base recurring sessions
- ✅ Edge cases (wrong weekday, invalid dates, etc.)
- ✅ Complete workflow integration tests

Expected coverage: **>80%**

---

## Example Workflow

This example demonstrates all key features:

### 1. Create a recurring Monday session starting Nov 4, 2024
```bash
curl -X POST http://localhost:8000/api/sessions/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Weekly Team Meeting",
    "session_type": "recurring",
    "start_datetime": "2024-11-04T10:00:00Z",
    "duration_minutes": 60,
    "recurrence_day": 0
  }'
```

### 2. List all sessions for November 2024
```bash
curl "http://localhost:8000/api/sessions/?start=2024-11-01T00:00:00Z&end=2024-11-30T23:59:59Z"
```
**Result**: Shows 4 occurrences (Nov 4, 11, 18, 25)

### 3. Cancel the Nov 18 occurrence
```bash
curl -X DELETE http://localhost:8000/api/sessions/1/occurrences/2024-11-18/
```

### 4. List sessions again
```bash
curl "http://localhost:8000/api/sessions/?start=2024-11-01T00:00:00Z&end=2024-11-30T23:59:59Z"
```
**Result**: Shows 3 occurrences (Nov 4, 11, 25) - Nov 18 is cancelled

### 5. Update Nov 25 occurrence to 11 AM
```bash
curl -X PATCH http://localhost:8000/api/sessions/1/occurrences/2024-11-25/ \
  -H "Content-Type: application/json" \
  -d '{"new_datetime": "2024-11-25T11:00:00Z"}'
```

### 6. Update base session time to 9 AM
```bash
curl -X PATCH http://localhost:8000/api/sessions/1/ \
  -H "Content-Type: application/json" \
  -d '{"start_datetime": "2024-11-04T09:00:00Z"}'
```

### 7. List sessions to see the results
```bash
curl "http://localhost:8000/api/sessions/?start=2024-11-01T00:00:00Z&end=2024-12-31T23:59:59Z"
```
**Result**: 
- Nov 4, 11 → 9 AM (updated base time)
- Nov 18 → cancelled
- Nov 25 → 11 AM (exception preserved)
- Dec 2, 9, 16, etc. → 9 AM (new base time)

---

## Project Structure

```
event-calendar/
├── event_calendar/          # Django project settings
│   ├── __init__.py
│   ├── settings.py         # Project settings
│   ├── urls.py             # Root URL configuration
│   ├── wsgi.py
│   └── asgi.py
├── sessions/                # Main app
│   ├── __init__.py
│   ├── models.py           # Session & SessionException models
│   ├── serializers.py      # DRF serializers
│   ├── views.py            # API views
│   ├── urls.py             # App URL routing
│   ├── admin.py            # Django admin configuration
│   ├── apps.py
│   └── tests.py            # Comprehensive test suite
├── manage.py               # Django management script
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

---

## Data Models

### Session
Stores both one-time and recurring sessions.

**Fields:**
- `title` - Session name
- `description` - Session description
- `session_type` - 'one_time' or 'recurring'
- `start_datetime` - First occurrence datetime
- `duration_minutes` - Session length
- `recurrence_day` - Weekday for recurring sessions (0-6)

### SessionException
Stores modifications to specific occurrences.

**Fields:**
- `session` - Foreign key to Session
- `exception_date` - Date of the occurrence
- `is_cancelled` - Whether this occurrence is cancelled
- `modified_datetime` - New datetime if moved

---

## Best Practices Implemented

✅ **Clean Architecture**: Separation of concerns with models, serializers, and views
✅ **Validation**: Comprehensive data validation at multiple levels
✅ **Error Handling**: Clear, actionable error messages
✅ **Documentation**: Detailed docstrings and comments
✅ **Testing**: >80% test coverage with unit and integration tests
✅ **RESTful Design**: Standard HTTP methods and status codes
✅ **Timezone Awareness**: All datetimes are timezone-aware (UTC)
✅ **Database Indexing**: Optimized queries with appropriate indexes
✅ **Type Safety**: Proper field types and constraints

---

## Future Enhancements

Potential improvements for production use:
- [ ] Add pagination for large result sets
- [ ] Add authentication and user-specific sessions
- [ ] Support for bi-weekly, monthly recurring patterns
- [ ] Email notifications for session reminders
- [ ] Conflict detection (overlapping sessions)
- [ ] Export to iCalendar format
- [ ] WebSocket support for real-time updates
- [ ] Rate limiting and throttling
- [ ] GraphQL API alternative

---

## License

MIT License - See LICENSE file for details

---

## Support

For issues, questions, or contributions, please open an issue on the repository.
