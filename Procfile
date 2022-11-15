release: ./manage.py migrate
web: gunicorn --bind 0.0.0.0:$PORT miqa.wsgi
# never use more than one worker; duplicate schedulers will result in duplicate tasks
worker: REMAP_SIGTERM=SIGQUIT celery --app miqa.celery worker --loglevel INFO --without-heartbeat -B
