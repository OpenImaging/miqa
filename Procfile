release: ./manage.py migrate
web: gunicorn --bind 0.0.0.0:$PORT miqa.wsgi
worker: REMAP_SIGTERM=SIGQUIT celery --app miqa.celery worker --loglevel INFO --without-heartbeat
