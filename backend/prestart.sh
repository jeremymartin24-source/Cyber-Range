#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Seeding database..."
python -m scripts.seed

echo "Starting application..."
exec "$@"
