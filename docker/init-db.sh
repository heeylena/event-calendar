#!/bin/bash
set -e

# This script runs when the PostgreSQL container is first initialized
# It ensures the database is ready for Django

echo "PostgreSQL initialization script executed"
echo "Database: $POSTGRES_DB"
echo "User: $POSTGRES_USER"
