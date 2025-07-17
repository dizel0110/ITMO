import functools
import logging
import os
from datetime import timedelta
from typing import Any, Optional

from celery import Celery

logger = logging.getLogger(__name__)


class CustomCeleryApp(Celery):
    """Provides decorators to prevent same task run concurrently with self
    Usage: @app.one_at_time_task(queue=<queue name>, blocking=False)
    Примечание:
            - if useing blocking=False tasks can be let in the worker.
            - If you do not supply timeout it will be taken from Celery settings.
            Do not set timeout, if there is no grounded expected limit to the task.

        Example:

        @app.one_at_time_task(timeout=60, blocking=True)
        def my_task():
            # your code
            pass"""

    @staticmethod
    def generate_lock_key(run_func: Any) -> str:
        """Returns
        str: Unique blocking key
        """
        key = f'{run_func.__module__}.{run_func.__qualname__}'
        return key

    def get_timeout(self, timeout: Optional[int] = None) -> int:
        """
        Returns:
            int: time in seconds till task blockage
        """

        timeout = timeout or self.conf.get('task_time_limit')
        if timeout and timeout > 0:
            return timeout
        raise ValueError('Укажите в настройках проекта CELERY_TASK_TIME_LIMIT или задайте timeout')

    def one_at_time_task(self, timeout: Optional[int] = None, blocking: bool = True, **kwargs: Any) -> Any:
        """
        Returns:
            Callable: func wrapped by decorators lock_task и task.
        """

        def _decorator(function: Any) -> Any:
            function_lock = self.lock_task(timeout=timeout, blocking=blocking)(function)

            function_lock = functools.update_wrapper(function_lock, function)

            function = self.task(function_lock, **kwargs)
            return function

        return _decorator

    def lock_task(self, timeout: Optional[int] = None, blocking: bool = True) -> Any:
        """
        Returns:
            Callable: wrapped func by decorator lock_task.
        """
        lock_timeout = self.get_timeout(timeout)

        def _decorator(run_func: Any) -> Any:
            def _caller(*args: Any, **kwargs: Any) -> Any:
                ret_value = None
                have_lock = False
                lock_key = self.generate_lock_key(run_func)
                logger.debug(f'Trying to get a lock on the key {lock_key} for {lock_timeout} seconds')
                lock = self.backend.client.lock(lock_key, timeout=lock_timeout)  # type: ignore[attr-defined]
                try:
                    have_lock = lock.acquire(blocking=blocking)
                    if have_lock:
                        logger.debug(f'Lock received by the key {lock_key} for {lock_timeout} seconds')
                        ret_value = run_func(*args, **kwargs)
                    else:
                        logger.debug(f'Refusal to block {lock_key}')
                finally:
                    if have_lock:
                        lock.release()
                        logger.debug(f'Key lock has been removed {lock_key}')

                return ret_value

            return _caller

        return _decorator


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nlp.settings')
app = CustomCeleryApp('nlp')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

PROCESS_PROTOCOLS_TIMEOUT = {'seconds': 300}
RETURN_PROTOCOLS_TO_PROCESSING_TIMEOUT = {'seconds': 3600}
SEND_PROTOCOLS_TO_GRAPHDB = {'minutes': 60}
DATA_STRUCTURE_CHECK_TIMEOUT = {'seconds': 86400}
REFRESH_GRAPHDB_STRUCTURE_TIMEOUT = {'hours': 24}
UPDATE_ENTITIES_PKL = {'minutes': 60}

app.conf.beat_schedule = {
    'process_protocols': {
        'task': 'nlp.utils.LLM.tasks.process_protocols',
        'schedule': timedelta(**PROCESS_PROTOCOLS_TIMEOUT),
        'options': {
            'queue': 'low',
        },
    },
    'return_failed_protocols_to_processing': {
        'task': 'nlp.utils.LLM.tasks.return_failed_protocols_to_processing',
        'schedule': timedelta(**RETURN_PROTOCOLS_TO_PROCESSING_TIMEOUT),
        'options': {
            'queue': 'default',
        },
    },
    'send_protocols_to_graphdb': {
        'task': 'nlp.apps.protocol.tasks.send_protocols_to_graphdb',
        'schedule': timedelta(**SEND_PROTOCOLS_TO_GRAPHDB),
        'options': {
            'queue': 'default',
        },
    },
    'check_neuro_graphdb_data_structure_concordance': {
        'task': 'nlp.apps.protocol.tasks.check_neuro_graphdb_data_structure_concordance',
        'schedule': timedelta(**DATA_STRUCTURE_CHECK_TIMEOUT),
        'options': {
            'queue': 'default',
        },
    },
    'refresh_graphdb_structure': {
        'task': 'nlp.apps.secret_settings.tasks.refresh_graphdb_structure',
        'schedule': timedelta(**REFRESH_GRAPHDB_STRUCTURE_TIMEOUT),
        'options': {
            'queue': 'default',
        },
    },
    'update_entities_pkl': {
        'task': 'nlp.utils.LLM.tasks.update_entities_pkl',
        'schedule': timedelta(**UPDATE_ENTITIES_PKL),
        'options': {
            'queue': 'default',
        },
    },
}
