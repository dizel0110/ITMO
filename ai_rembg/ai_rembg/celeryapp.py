import os
from datetime import timedelta

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_photoenhancer.settings')
app = Celery('ai_photoenhancer')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

CLEAR_OLD_IMAGES_TIMEOUT = {'minutes': 60}
PROCESS_IMAGES_TIMEOUT = {'seconds': 30}

app.conf.beat_schedule = {
    'clean_old_images': {
        'task': 'ai_photoenhancer.apps.background_remover.tasks.clear_old_images',
        'schedule': timedelta(**CLEAR_OLD_IMAGES_TIMEOUT),
    },
    'process_images': {
        'task': 'ai_photoenhancer.apps.background_remover.tasks.process_images',
        'schedule': timedelta(**PROCESS_IMAGES_TIMEOUT),
    },
}
