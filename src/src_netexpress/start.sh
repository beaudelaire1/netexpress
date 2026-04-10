#!/bin/bash

echo "Starting migrations in background..."
python manage.py migrate --noinput &

echo "Starting Gunicorn..."
exec gunicorn netexpress.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120
