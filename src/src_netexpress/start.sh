#!/bin/bash
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Gunicorn..."
exec gunicorn netexpress.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4
