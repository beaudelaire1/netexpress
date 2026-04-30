#!/bin/bash

echo "Running migrations..."
python manage.py migrate --noinput

echo "Ensuring superuser exists..."
python manage.py ensure_superuser

echo "Collecting static files..."
python manage.py collectstatic --noinput 2>/dev/null || true

echo "Starting Gunicorn..."
exec gunicorn netexpress.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120
