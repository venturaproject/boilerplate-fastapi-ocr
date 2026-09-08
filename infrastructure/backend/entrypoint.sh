#!/bin/sh
set -e

cd /app/backend

until pg_isready -h "$DB_HOST" -p "${DB_PORT:-5432}" -U "$DB_USER"; do
    echo "Waiting for postgres..."
    sleep 1
done

echo "Running migrations..."
uv run alembic upgrade head

echo "Running seed..."
uv run python seed.py

echo "Starting server..."
# --proxy-headers: trust X-Forwarded-* from nginx so request.client.host is the
# real client IP (rate-limit buckets, logs). Safe because the backend port is
# never published — nginx is the only ingress.
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 \
    --proxy-headers --forwarded-allow-ips '*'
