#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

if [ -z "$SKIP_SEED" ]; then
  echo "Seeding database..."
  python -m scripts.seed
fi

echo "Starting application..."
exec "$@"
