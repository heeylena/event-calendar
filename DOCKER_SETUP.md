# Docker Setup Guide

This project uses **Docker Compose for PostgreSQL database** while **Django runs locally**. This is a common development setup that provides production-like database while maintaining local development flexibility.

---

## 🏗️ Architecture

```
┌─────────────────────┐
│   Django (Local)    │
│   Port: 8000        │
│   Python/venv       │
└──────────┬──────────┘
           │
           │ Connection
           │ localhost:5432
           ▼
┌─────────────────────┐
│  PostgreSQL (Docker)│
│   Port: 5432        │
│   Container         │
└─────────────────────┘
```

---

## 📋 Prerequisites

- Python 3.10+
- Docker Desktop installed and running
- Docker Compose (included with Docker Desktop)

---

## 🚀 Quick Start

### 1. Copy Environment File

```bash
cp .env.example .env
```

The default values in `.env` are ready to use:
```env
DB_ENGINE=postgresql
DB_NAME=event_calendar
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
```

### 2. Start PostgreSQL Container

```bash
docker-compose up -d
```

This will:
- Download PostgreSQL 15 image (if not already downloaded)
- Create and start the database container
- Create a persistent volume for data
- Expose port 5432 on localhost

### 3. Verify Database is Running

```bash
docker-compose ps
```

You should see:
```
NAME                  STATUS    PORTS
event_calendar_db     Up        0.0.0.0:5432->5432/tcp
```

Check health:
```bash
docker-compose logs db
```

### 4. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (includes psycopg2)
pip install -r requirements.txt
```

### 5. Run Django Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create Superuser (Optional)

```bash
python manage.py createsuperuser
```

### 7. Start Django Development Server

```bash
python manage.py runserver
```

✅ **Done!** Django is running locally and connected to PostgreSQL in Docker.

---

## 🔧 Configuration

### Environment Variables

Edit `.env` to customize:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Settings
DB_ENGINE=postgresql
DB_NAME=event_calendar
DB_USER=postgres
DB_PASSWORD=your-secure-password
DB_HOST=localhost
DB_PORT=5432
```

### Using SQLite Instead (Testing)

If you want to use SQLite for quick testing:

```env
DB_ENGINE=sqlite
```

No Docker needed - Django will use `db.sqlite3` file.

---

## 🐳 Docker Commands

### Start Database
```bash
docker-compose up -d
```

### Stop Database
```bash
docker-compose stop
```

### Stop and Remove Container
```bash
docker-compose down
```

### Stop and Remove Container + Data
```bash
docker-compose down -v
```
⚠️ This deletes all data!

### View Logs
```bash
docker-compose logs -f db
```

### Access PostgreSQL Shell
```bash
docker-compose exec db psql -U postgres -d event_calendar
```

Then you can run SQL:
```sql
\dt  -- List tables
\d booking_sessions_session  -- Describe table
SELECT * FROM booking_sessions_session;
```

### Restart Database
```bash
docker-compose restart db
```

---

## 🗄️ Database Management

### Backup Database

```bash
docker-compose exec db pg_dump -U postgres event_calendar > backup.sql
```

### Restore Database

```bash
cat backup.sql | docker-compose exec -T db psql -U postgres event_calendar
```

### Reset Database

```bash
# Stop Django server first
docker-compose down -v
docker-compose up -d
python manage.py migrate
```

---

## 🧪 Testing

### Run Tests with PostgreSQL

```bash
# Make sure Docker is running
docker-compose up -d

# Run tests
python manage.py test sessions
```

### Run Tests with SQLite (Faster)

Create `.env.test`:
```env
DB_ENGINE=sqlite
```

Then:
```bash
python manage.py test sessions --settings=event_calendar.settings
```

---

## 🔍 Troubleshooting

### Issue: "Connection refused" or "could not connect to server"

**Solution:**
```bash
# Check Docker is running
docker ps

# Check database status
docker-compose ps

# Check logs
docker-compose logs db

# Restart
docker-compose restart db
```

### Issue: "Port 5432 already in use"

**Solution:** You have another PostgreSQL instance running.

**Option 1:** Stop local PostgreSQL
```bash
# macOS
brew services stop postgresql

# Linux
sudo systemctl stop postgresql
```

**Option 2:** Change port in `.env`
```env
DB_PORT=5433
```

And in `docker-compose.yml`:
```yaml
ports:
  - "5433:5432"
```

### Issue: "password authentication failed"

**Solution:** Recreate container with new password
```bash
docker-compose down -v
# Update password in .env
docker-compose up -d
python manage.py migrate
```

### Issue: Migrations not applying

**Solution:**
```bash
# Check database connection
docker-compose exec db psql -U postgres -d event_calendar -c "SELECT 1;"

# Force recreate migrations
python manage.py migrate --run-syncdb
```

---

## 📊 Checking Database Connection

### From Django Shell

```bash
python manage.py shell
```

```python
from django.db import connection
print(connection.settings_dict)
# Should show PostgreSQL settings

# Test query
from sessions.models import Session
print(Session.objects.count())
```

### Direct Connection Test

```bash
docker-compose exec db psql -U postgres -d event_calendar -c "\dt"
```

Should list your Django tables.

---

## 🎯 Why This Setup?

### Benefits of Docker Database + Local Django

✅ **Production-like**: PostgreSQL matches production environment
✅ **Isolated**: Database runs in container, doesn't affect system
✅ **Easy cleanup**: `docker-compose down -v` removes everything
✅ **Fast development**: No need to rebuild Django container
✅ **Easy debugging**: Django runs locally with full IDE support
✅ **Team consistency**: Everyone uses same database version

### When to Use

- ✅ Development with production-like database
- ✅ Testing PostgreSQL-specific features
- ✅ Team collaboration (consistent environment)

### When to Use SQLite

- ✅ Quick testing
- ✅ CI/CD pipelines
- ✅ Simple demos
- ✅ When Docker isn't available

---

## 🔄 Switching Between Databases

### To PostgreSQL

1. Update `.env`:
```env
DB_ENGINE=postgresql
```

2. Start Docker:
```bash
docker-compose up -d
```

3. Migrate:
```bash
python manage.py migrate
```

### To SQLite

1. Update `.env`:
```env
DB_ENGINE=sqlite
```

2. Stop Docker (optional):
```bash
docker-compose down
```

3. Migrate:
```bash
python manage.py migrate
```

---

## 📈 Performance Tips

### PostgreSQL Tuning (Optional)

Add to `docker-compose.yml` under `db` → `environment`:
```yaml
POSTGRES_INITDB_ARGS: "-E UTF8 --locale=C"
```

Add to `docker-compose.yml` under `db` → `command`:
```yaml
command: postgres -c shared_buffers=256MB -c max_connections=200
```

---

## 🎓 For Interview

When discussing the database setup:

**Say:**
> "I use Docker Compose for the PostgreSQL database while Django runs locally. This gives me a production-like environment without the overhead of containerizing the entire application during development. It's easy to tear down and recreate, and ensures the entire team uses the same database version."

**Show:**
1. `.env` file for configuration
2. `docker-compose.yml` - simple, clean setup
3. `settings.py` - dynamic database configuration
4. Run `docker-compose ps` to show it's running

**Benefits:**
- Production parity (PostgreSQL)
- Easy to demonstrate
- Shows DevOps awareness
- Clean separation of concerns

---

## 📝 Quick Commands Cheat Sheet

```bash
# Start everything
docker-compose up -d && source venv/bin/activate && python manage.py runserver

# Stop everything
docker-compose stop

# Fresh start
docker-compose down -v && docker-compose up -d && python manage.py migrate

# View database
docker-compose exec db psql -U postgres -d event_calendar

# Backup
docker-compose exec db pg_dump -U postgres event_calendar > backup.sql

# Logs
docker-compose logs -f db
```

---

## ✅ Verification Checklist

- [ ] Docker Desktop is running
- [ ] `.env` file exists with correct values
- [ ] `docker-compose ps` shows db as "Up"
- [ ] `docker-compose logs db` shows no errors
- [ ] `python manage.py migrate` runs successfully
- [ ] `python manage.py test sessions` all tests pass
- [ ] Can create sessions via API
- [ ] Can view data in PostgreSQL shell

---

## 🆘 Support

If you encounter issues:

1. Check Docker Desktop is running
2. Check logs: `docker-compose logs db`
3. Try recreating: `docker-compose down -v && docker-compose up -d`
4. Check `.env` file has correct settings
5. Verify port 5432 isn't in use: `lsof -i :5432`

---

**Status**: ✅ Production-ready Docker setup for PostgreSQL database
