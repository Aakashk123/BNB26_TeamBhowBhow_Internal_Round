#!/bin/sh
set -eu
cd /app/backend
alembic upgrade head
PYTHONPATH=/app/backend:/app/sdk/python python /app/scripts/init_chain.py
if [ "${ENABLE_DEMO:-false}" = "true" ]; then
  PYTHONPATH=/app/backend:/app/sdk/python python -m app.seed.demo
fi
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --no-access-log
