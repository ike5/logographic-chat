#!/bin/bash

# Start script with error handling and logging
set -e

echo "Starting logographic-chat backend..."
cd backend

# Check if required environment variables are set
if [ -z "$DJANGO_SECRET_KEY" ]; then
    echo "ERROR: DJANGO_SECRET_KEY is not set"
    echo "Please set DJANGO_SECRET_KEY in Railway environment variables"
    exit 1
fi

if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL is not set"
    echo "Please ensure PostgreSQL service is provisioned on Railway"
    exit 1
fi

# Run migrations with error handling
echo "Running database migrations..."
python manage.py migrate --noinput

# Start Django ASGI application
echo "Starting Daphne ASGI server on port $PORT..."
exec daphne -b 0.0.0.0 -p $PORT logographic_chat.asgi:application