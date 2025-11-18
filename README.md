# Event Calendar Backend - Django REST API

A production-ready REST API for session booking with support for one-time and recurring weekly sessions.

## Features

- ✅ Create recurring session patterns (weekly)
- ✅ Auto-generate occurrences for future dates
- ✅ Create one-time sessions
- ✅ Cancel or reschedule individual occurrences
- ✅ Query sessions by date range
- ✅ Clean architecture (Services → Managers → Models)
- ✅ 35 comprehensive tests (>85% coverage)

## Quick Start

### 1. Setup (Automated with Docker)

```bash
chmod +x setup-docker.sh
./setup-docker.sh
```

This starts PostgreSQL, creates a virtual environment, installs dependencies, and runs migrations.

### 2. Run Server

```bash
source venv/bin/activate
python manage.py runserver
```

**Access:**
- API: http://localhost:8000/api/
- Admin: http://localhost:8000/admin/

### 3. Generate Future Occurrences

```bash
python manage.py generate_occurrences --months 3
```

---

## API Quick Reference

### Endpoints

#### Recurrence Patterns
- `POST /api/patterns/` - Create recurring pattern
- `GET /api/patterns/` - List all patterns
- `PATCH /api/patterns/{id}/` - Update pattern
- `DELETE /api/patterns/{id}/` - Delete pattern

#### Session Occurrences
- `POST /api/occurrences/` - Create one-time session
- `GET /api/occurrences/?start=X&end=Y` - List sessions in date range
- `PATCH /api/occurrences/{id}/` - Update session
- `DELETE /api/occurrences/{id}/` - Cancel session
- `POST /api/occurrences/{id}/complete/` - Mark as completed

### Example: Create Recurring Pattern

```bash
curl -X POST http://localhost:8000/api/patterns/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Weekly Team Meeting",
    "weekday": 1,
    "time": "14:00:00",
    "start_date": "2024-11-01",
    "duration_minutes": 60
  }'
```

**Weekday values:** 0=Monday, 1=Tuesday, ..., 6=Sunday

---

## Testing

```bash
python manage.py test sessions

pip install coverage
coverage run --source='.' manage.py test sessions
coverage report
```

**Coverage: >85%** - Tests cover models, managers, services, API endpoints, and integration workflows.

---

## Architecture

**Layered Design:**
```
Views (API) → Services (Business Logic) → Managers (Queries) → Models (Data)
```

**Key Files:**
- `sessions/models.py` - RecurrencePattern & SessionOccurrence models
- `sessions/services.py` - Business logic layer
- `sessions/managers.py` - Custom query methods
- `sessions/views.py` - Thin API views
- `sessions/tests.py` - 35 comprehensive tests

**Occurrence Materialization Pattern:**
- RecurrencePattern: Template for recurring sessions
- SessionOccurrence: All actual bookable instances (one-time + recurring)
- Benefits: Fast queries, easy modifications, clear data model

---

## License

MIT License
