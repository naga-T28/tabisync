#!/bin/bash

# DBが起動するまで待機（Postgresを使ってる場合など）
# Uncomment if needed
# while ! nc -z db 5432; do sleep 1; done

python manage.py makemigrations --noinput
python manage.py migrate --noinput
exec "$@"

