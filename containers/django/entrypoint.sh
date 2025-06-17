#!/bin/bash

# DBが起動するまで待機（Postgresを使ってる場合など）
# Uncomment if needed
# while ! nc -z db 5432; do sleep 1; done

python3 project_tabisync/manage.py collectstatic --noinput
python3 project_tabisync/manage.py makemigrations --noinput
python3 project_tabisync/manage.py migrate --noinput
exec "$@"

