#!/bin/bash
# Complete setup script with Docker database

set -e  # Exit on error

echo "🚀 Setting up Event Calendar Backend with Docker PostgreSQL..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop and try again."
    exit 1
fi

# Step 1: Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file"
else
    echo "✅ .env file already exists"
fi

# Step 2: Start Docker database
echo ""
echo "🐳 Starting PostgreSQL database in Docker..."
docker-compose up -d

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 5

# Check if database is healthy
if docker-compose ps | grep -q "Up"; then
    echo "✅ PostgreSQL database is running"
else
    echo "❌ Failed to start database"
    echo "   Check logs with: docker-compose logs db"
    exit 1
fi

# Step 3: Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo ""
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Step 4: Activate virtual environment and install dependencies
echo ""
echo "📥 Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt

echo "✅ Dependencies installed"

# Step 5: Run migrations
echo ""
echo "🗄️  Running database migrations..."
python manage.py makemigrations
python manage.py migrate

echo "✅ Migrations completed"

# Step 6: Run tests
echo ""
echo "🧪 Running tests..."
python manage.py test sessions

echo ""
echo "✨ Setup complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎯 Next steps:"
echo ""
echo "  1. Activate virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Start Django server:"
echo "     python manage.py runserver"
echo ""
echo "  3. Access the API:"
echo "     http://localhost:8000/api/"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📚 Useful commands:"
echo ""
echo "  • View database logs:"
echo "    docker-compose logs -f db"
echo ""
echo "  • Access PostgreSQL shell:"
echo "    docker-compose exec db psql -U postgres -d event_calendar"
echo ""
echo "  • Stop database:"
echo "    docker-compose stop"
echo ""
echo "  • Restart database:"
echo "    docker-compose restart db"
echo ""
echo "  • See full documentation:"
echo "    cat DOCKER_SETUP.md"
echo ""
