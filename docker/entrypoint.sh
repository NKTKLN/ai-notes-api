#!/bin/sh
set -e

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting FastAPI..."
exec uvicorn ai_notes_api.main:app --app-dir src --host 0.0.0.0 --port 8000
