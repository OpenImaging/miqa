from datetime import timedelta
import os

from celery import Celery
import configurations.importer
from django.conf import settings

os.environ['DJANGO_SETTINGS_MODULE'] = 'miqa.settings'
if not os.environ.get('DJANGO_CONFIGURATION'):
    raise ValueError('The environment variable "DJANGO_CONFIGURATION" must be set.')
configurations.importer.install()

# Using a string config_source means the worker doesn't have to serialize
# the configuration object to child processes.
app = Celery(config_source='django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

if settings.DEMO_MODE:
    app.conf.beat_schedule = {
        'reset-demo': {
            'task': 'miqa.core.tasks.reset_demo',
            'schedule': timedelta(days=1),
        }
    }
