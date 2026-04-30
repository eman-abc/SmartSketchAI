#!/bin/bash
set -e

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Gunicorn server..."
exec gunicorn smartsketch_backend.wsgi:application --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads 2 --timeout 120
