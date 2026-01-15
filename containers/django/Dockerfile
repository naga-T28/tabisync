FROM python:3.8-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /code

# 基本ツール
RUN pip install --upgrade pip && pip install pipenv

# Pipfile / Pipfile.lock の反映
COPY ./Pipfile /code/Pipfile
COPY ./Pipfile.lock /code/Pipfile.lock

# pipenv install はまだ実行しない（←順番変更）
# アプリケーションコードを先にコピー
COPY . /code/

# ここで pipenv install（manage.py も static も存在するタイミング）
RUN pipenv install --system --deploy --ignore-pipfile

# エントリーポイントを登録
COPY ./containers/django/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Gunicornでアプリ起動（runserverではなく）
CMD ["gunicorn", "project_tabisync.wsgi:application", "--bind", "0.0.0.0:8000"]


# ...前略...


