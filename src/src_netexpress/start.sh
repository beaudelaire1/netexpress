#!/bin/sh
set -eu
# Migrations run once in the separate migrate service, never in each web worker.
exec gunicorn netexpress.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers "${WEB_CONCURRENCY:-2}" --threads 4 --timeout 120 --access-logfile - --error-logfile -
