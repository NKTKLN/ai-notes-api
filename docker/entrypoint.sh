#!/bin/sh
set -e

ROLE="${1:-api}"

case "$ROLE" in
  api)
    echo "Running Alembic migrations..."
    alembic upgrade head

    echo "Starting FastAPI..."
    exec uvicorn ai_notes_api.main:app --app-dir src --host 0.0.0.0 --port 8000
    ;;
  worker)
    echo "Starting Celery worker..."
    exec celery -A ai_notes_api.workers.celery_app.celery_app worker --loglevel=info
    ;;
  *)
    echo "Running custom command: $*"
    exec "$@"
    ;;
esac
