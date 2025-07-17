"""
Module for celery tasks for Yandex GPT.
=======================================

Functions:
----------
update_quotes_gpt

Dependencies:
-------------
django
\nlogging

"""


import logging

from django.core.cache import cache

from akcent_graph.apps.secret_settings.models import YGPTSettings
from akcent_graph.celeryapp import app

logger = logging.getLogger(__name__)


@app.task(ignore_results=True)
def update_quotes_gpt() -> None:
    ygpt_settings = YGPTSettings.objects.first()
    if ygpt_settings:
        default_sync = ygpt_settings.sync_quota_per_hour
        default_async = ygpt_settings.async_quota_per_hour
    else:
        default_sync = 0
        default_async = 0

    cache.set(
        'sync_quota_per_hour',
        default_sync,
        timeout=60 * 60,
    )
    cache.set(
        'async_quota_per_hour',
        default_async,
        timeout=60 * 60,
    )
    logger.info('YandexGPT quotes updated')
