import os
from datetime import timedelta

from celery import Celery
from celery.schedules import crontab

UPDATE_QUOTES_GPT_TIMEOUT = {'minutes': 60}
MARKING_NEW_PROTOCOLS = {'minutes': 15}
ADDITIONAL_MARKING_PROTOCOLS = {'hours': 1}
LOAD_NEW_PROTOCOLS_TIMEOUT = {'seconds': 1800}
GET_UPDATED_ANAMNESES_TIMEOUT = {'seconds': 1800}  # must be in seconds!
PREPARE_GRAPHDB_STRUCTURE_SCHEDULE = {'minute': '1', 'hour': '2'}
DOWNLOAD_EMBEDDINGS_FROM_S3_SCHEDULE = {'minute': '0', 'hour': '4'}
NEOSPIDER_CHECK_AND_CHANGE_SCHEDULE = {'minute': '0', 'hour': '5'}
NEOSPIDER_DELETE_BRIEF_DOUBLES_SCHEDULE = {'minute': '0', 'hour': '6'}
NEOSPIDER_NEODISEASE_NODES_CHECKER_SCHEDULE = {'minute': '0', 'hour': '7'}

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'akcent_graph.settings')
app = Celery('akcent_graph')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'update_quotes_gpt': {
        'task': 'akcent_graph.utils.clients.gpt.tasks.update_quotes_gpt',
        'schedule': timedelta(**UPDATE_QUOTES_GPT_TIMEOUT),
        'options': {
            'queue': 'low',
        },
    },
    'marking_new_protocols': {
        'task': 'akcent_graph.apps.feature_classifier.tasks.marking_new_protocols',
        'schedule': timedelta(**MARKING_NEW_PROTOCOLS),
        'options': {
            'queue': 'new_med_features',
        },
    },
    'additional_marking_protocols': {
        'task': 'akcent_graph.apps.feature_classifier.tasks.additional_marking_protocols',
        'schedule': timedelta(**ADDITIONAL_MARKING_PROTOCOLS),
        'options': {
            'queue': 'additional_med_features',
        },
    },
    'load_new_protocols_to_graphdb': {
        'task': 'akcent_graph.apps.medaggregator.tasks.load_new_protocols_to_graphdb',
        'schedule': timedelta(**LOAD_NEW_PROTOCOLS_TIMEOUT),
        'options': {
            'queue': 'default',
        },
    },
    'get_updated_anamneses_from_graphdb': {
        'task': 'akcent_graph.apps.medaggregator.tasks.get_updated_anamneses_from_graphdb',
        'schedule': timedelta(**GET_UPDATED_ANAMNESES_TIMEOUT),
        'options': {
            'queue': 'default',
        },
    },
    'prepare_graphdb_structure_with_parents': {
        'task': 'akcent_graph.apps.medaggregator.tasks.prepare_graphdb_structure_with_parents',
        'schedule': crontab(**PREPARE_GRAPHDB_STRUCTURE_SCHEDULE),
        'options': {
            'queue': 'default',
        },
    },
    'download_embeddings_from_s3': {
        'task': 'akcent_graph.apps.secret_settings.tasks.download_embeddings_from_s3',
        'schedule': crontab(**DOWNLOAD_EMBEDDINGS_FROM_S3_SCHEDULE),
        'options': {
            'queue': 'default',
        },
    },
    'neospider_check_and_change': {
        'task': 'akcent_graph.apps.medaggregator.tasks.neospider_check_and_change',
        'schedule': crontab(**NEOSPIDER_CHECK_AND_CHANGE_SCHEDULE),
        'options': {
            'queue': 'default',
        },
    },
    'neospider_delete_brief_doubles': {
        'task': 'akcent_graph.apps.medaggregator.tasks.neospider_delete_brief_doubles',
        'schedule': crontab(**NEOSPIDER_DELETE_BRIEF_DOUBLES_SCHEDULE),
        'options': {
            'queue': 'default',
        },
    },
    'neospider_neodisease_nodes_checker': {
        'task': 'akcent_graph.apps.medaggregator.tasks.neospider_neodisease_nodes_checker',
        'schedule': crontab(**NEOSPIDER_NEODISEASE_NODES_CHECKER_SCHEDULE),
        'options': {
            'queue': 'default',
        },
    },
}
