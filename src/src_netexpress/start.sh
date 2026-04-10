#!/bin/bash

echo "Running migrations (timeout 60s)..."
timeout 60 python manage.py migrate --noinput || echo "[WARN] Migrations skipped or timed out — will retry next deploy"

echo "Starting Gunicorn..."
exec gunicorn netexpress.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120
