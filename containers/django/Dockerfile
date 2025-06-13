FROM python:3.10

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /code

# 基本ツール
RUN pip install --upgrade pip && pip install pipenv

# Pipfile / Pipfile.lockの反映
COPY ./Pipfile /code/Pipfile
COPY ./Pipfile.lock /code/Pipfile.lock

RUN pipenv install --system --deploy --ignore-pipfile

# アプリケーションコードをすべてコピー（ここが重要）
COPY . /code/

# collectstatic 実行（静的ファイルの準備）
RUN python manage.py collectstatic --noinput

# エントリーポイントを登録
COPY ./containers/django/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Gunicornでアプリ起動（runserverではなく）
CMD ["gunicorn", "project_tabisync.wsgi:application", "--bind", "0.0.0.0:8000"]
