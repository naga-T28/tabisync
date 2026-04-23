#!/bin/bash
set -e

cd /code/project_tabisync

echo "[entrypoint] Starting Django container setup..."
# DBが起動するまで待機（Postgresを使ってる場合など）
# Uncomment if needed
# while ! nc -z db 5432; do sleep 1; done

echo "[entrypoint] Running collectstatic..."
python3 manage.py collectstatic --noinput
echo "[entrypoint] collectstatic completed."

echo "[entrypoint] Running makemigrations..."
python3 manage.py makemigrations --noinput
echo "[entrypoint] makemigrations completed."

echo "[entrypoint] Running migrate..."
python3 manage.py migrate --noinput
echo "[entrypoint] migrate completed."

echo "[entrypoint] Starting gunicorn..."
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-60}"
GUNICORN_GRACEFUL_TIMEOUT="${GUNICORN_GRACEFUL_TIMEOUT:-10}"
exec gunicorn project_tabisync.wsgi:application \
  --bind 0.0.0.0:8000 \
  --timeout "${GUNICORN_TIMEOUT}" \
  --graceful-timeout "${GUNICORN_GRACEFUL_TIMEOUT}"
