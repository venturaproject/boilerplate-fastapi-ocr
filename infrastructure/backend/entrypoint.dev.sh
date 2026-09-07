#!/bin/sh
set -e

cd /app/backend

# Install the OCR engine extras unless OCR is stubbed out (OCR_ENGINE=fake).
if [ "${OCR_ENGINE:-paddle}" = "fake" ]; then
    uv sync
else
    uv sync --extra paddle --extra tesseract
fi

until pg_isready -h "$DB_HOST" -p "${DB_PORT:-5432}" -U "$DB_USER"; do
    echo "Waiting for postgres..."
    sleep 1
done

echo "Running migrations..."
uv run alembic upgrade head

echo "Running seed..."
uv run python seed.py

echo "Starting dev server..."
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
