import os
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any

import dj_database_url
import sentry_sdk
from corsheaders.defaults import default_headers
from decouple import Csv, config
from django.utils.translation import gettext_lazy as _
from kombu import Queue
from neomodel import config as neo_config
from sentry_sdk.integrations.django import DjangoIntegration

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_DIR = os.path.join(BASE_DIR, 'akcent_graph')

sys.path.append(PROJECT_DIR)

SECRET_KEY = config(
    'SECRET_KEY',
    default='django-insecure-gz)4x2qursui^1&d5*)jj7jd40ioez4yaxyac5fc%w6wepye&1',
)

ENV = config('ENV', default='production')
DEBUG = config('DEBUG', default=False, cast=bool)


ALLOWED_HOSTS = []
AUTH_USER_MODEL = 'common.User'

ALLOW_DEV_APPS = config('ALLOW_DEV_APPS', default=False, cast=bool)

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'constance',
    'constance.backends.database',
    'corsheaders',
    'django_celery_beat',
    'rest_framework',
    'rest_framework_simplejwt',
    'django_neomodel',
    'django_redis',
    'cacheops',
    'rangefilter',
]

LOCAL_APPS = [
    'akcent_graph.apps.common',
    'akcent_graph.apps.medaggregator',
    'akcent_graph.apps.secret_settings',
    'akcent_graph.apps.feature_classifier',
    'akcent_graph.utils.clients.gpt',
]

DEV_APPS = [
    'django_migration_linter',
]

INSTALLED_APPS += THIRD_PARTY_APPS
INSTALLED_APPS += LOCAL_APPS
if ALLOW_DEV_APPS:
    INSTALLED_APPS += DEV_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'query_counter.middleware.DjangoQueryCounterMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'akcent_graph.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'akcent_graph/templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'akcent_graph.wsgi.application'


# Database
DATABASE_URL = config('DATABASE_URL', default='postgres://postgres:postgres@db:5432/akcent_graph')
DATABASES = {'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)}
REDIS_URL = config('REDIS_URL', default='redis://redis:6379/0')
DATA_UPLOAD_MAX_NUMBER_FIELDS = 100000
NEOMODEL_NEO4J_BOLT_URL = config('NEO4J_BOLT_URL', default='bolt://neo4j:foobar01@127.0.0.1:7687')
neo_config.DATABASE_URL = NEOMODEL_NEO4J_BOLT_URL

# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
LANGUAGE_CODE = 'ru'
LANGUAGES = (
    ('ru', _('Russian')),
    ('en', _('English')),
)
LOCALE_PATHS = (os.path.join(PROJECT_DIR, 'locale'),)

TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'

STATICFILES_DIRS = [os.path.join(PROJECT_DIR, 'static')]

STATIC_ROOT = config('STATIC_ROOT')
if not STATIC_ROOT:
    STATIC_ROOT = os.path.join(BASE_DIR, 'public', 'static')

MEDIA_URL = '/media/'
MEDIA_ROOT = config('MEDIA_ROOT')
if not MEDIA_ROOT:
    MEDIA_ROOT = os.path.join(BASE_DIR, 'public', 'media')

# --------------------------------- SECURITY ----------------------------------
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')
USE_X_FORWARDED_HOST = True

ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())
ADDITIONAL_CSRF_TRUSTED_ORIGINS = config('ADDITIONAL_CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

HOST_IP_ADDRESS = config('HOST_IP_ADDRESS', default='http://127.0.0.1') or 'http://127.0.0.1'
HOSTNAME = config('AKCENT_GRAPH_HOSTNAME', default=HOST_IP_ADDRESS) or HOST_IP_ADDRESS
CSRF_TRUSTED_ORIGINS = [
    HOSTNAME,
    HOSTNAME + ':8000',
    HOST_IP_ADDRESS,
    HOST_IP_ADDRESS + ':8000',
    *ADDITIONAL_CSRF_TRUSTED_ORIGINS,
]

# --------------------------------- LOGGING -----------------------------------
LOG_LEVEL = config('LOG_LEVEL', default='WARNING', cast=str).upper()
LOG_DIR = config('LOG_DIR', default=None)
LOG_FILE_SIZE = config('LOG_FILE_SIZE', default=4096, cast=int)

LOGGING: dict[str, Any] = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '[{asctime}] {levelname:8} | {module:>10} @ {lineno:<5} | {message}',
            'datefmt': '%Y-%m-%d %H:%M:%S',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
        'propagate': True,
    },
    'celery.task': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
        'propagate': False,
    },
    'loggers': {
        'spnego': {'level': 'WARNING'},
        'asyncio': {'level': 'WARNING'},
        'django.server': {'handlers': ['console']},
        'django.utils.autoreload': {'level': 'WARNING'},
    },
}

if LOG_DIR:
    log_dir = Path(LOG_DIR)
    log_dir.mkdir(exist_ok=True)
    LOGGING['root']['handlers'].append('file')
    LOGGING['handlers']['file'] = {
        'filename': log_dir / 'akcent_graph.log',
        'class': 'logging.handlers.RotatingFileHandler',
        'maxBytes': 1024 * LOG_FILE_SIZE,
        'backupCount': 10,
        'formatter': 'default',
    }

# --------------------------------- SENTRY -----------------------------------
WITH_SENTRY = config('WITH_SENTRY', default=False, cast=bool)

if WITH_SENTRY:
    sentry_sdk.init(
        dsn=config('SENTRY_DSN'),
        integrations=[DjangoIntegration()],
    )

# ---------------------------------- CELERY -----------------------------------
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TIMEZONE = TIME_ZONE
CELERYD_HIJACK_ROOT_LOGGER = False
CELERY_DEFAULT_QUEUE = 'default'
CELERY_TASK_DEFAULT_QUEUE = 'default'

CELERY_QUEUES = (Queue('default', routing_key='default'),)
CELERY_TASK_QUEUES = {
    'default': {
        'binding_key': 'default',
    },
    'low': {
        'binding_key': 'low',
    },
    'new_med_features': {
        'binding_key': 'new_med_features',
    },
    'additional_med_features': {
        'binding_key': 'additional_med_features',
    },
}
FAILED_TASK_RETRY_COUNTDOWN = config('FAILED_TASK_RETRY_COUNTDOWN', default=600, cast=int)

# ------------------------------ CUSTOM SETTINGS ------------------------------
PRODUCT_TITLE = _('Akcent graph')
PRODUCT_VERSION = config('PRODUCT_VERSION', default='dev version')
APPLICATION_UID = config('APPLICATION_UID', None)
LICENSE_CHECK_URL = config('LICENSE_CHECK_URL', default='https://lic.iambulant.ru:8000/auth_server/check_license/')
LICENSE_SUCCESSFUL_CHECK_TIMEOUT = config('LICENSE_SUCCESSFUL_CHECK_TIMEOUT', cast=int, default=24 * 60 * 60)
LICENSE_FAILED_CHECK_TIMEOUT = config('LICENSE_FAILED_CHECK_TIMEOUT', cast=int, default=300)
LICENSE_COMPANY_UID = config('LICENSE_COMPANY_UID', default='59de36c5-d1c1-4c1b-ba06-ced79d219cf5')
LICENSE_SERVER_S3_DISPATCHER = config(
    'LICENSE_SERVER_S3_DISPATCHER',
    default='https://lic.iambulant.ru:8000/releases/extra/',
)
PROCESSED_IMAGES_STORE_TIME = config('PROCESSED_IMAGES_STORE_TIME', cast=int, default=2)  # hours
RETURNED_IMAGES_STORE_TIME = config('RETURNED_IMAGES_STORE_TIME', cast=int, default=1)  # hours
GRAPHDB_STRUCTURE_JSON = config(
    'GRAPHDB_STRUCTURE_JSON',
    default=os.path.join(BASE_DIR, 'private', 'graphdb_structure_with_parents.json'),
)

# ------------------------------- REST FRAMEWORK ------------------------------
REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_AUTHENTICATION_CLASSES': ('akcent_graph.apps.common.authentication.CustomJWTStatelessUserAuthentication',),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

CORS_ALLOW_CREDENTIALS = True
CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_HEADERS = list(default_headers) + []

# -------------------------------- CONSTANCE ----------------------------------
CONSTANCE_BACKEND = 'akcent_graph.utils.constance.DatabaseBackend'

CONSTANCE_ADDITIONAL_FIELDS = {
    'one_line': ('django.forms.fields.CharField', {'required': False}),
    'read_only_one_line': (
        'django.forms.fields.CharField',
        {'disabled': True, 'required': False},
    ),
    'percent': (
        'django.forms.fields.IntegerField',
        {'required': False, 'max_value': 99},
    ),
    'read_only_percent': (
        'django.forms.fields.IntegerField',
        {'disabled': True, 'required': False, 'max_value': 99},
    ),
    'password': (
        'django.forms.fields.CharField',
        {
            'widget': 'django.forms.PasswordInput',
            'required': False,
            'widget_kwargs': {'render_value': True},
        },
    ),
    'read_only_password': (
        'django.forms.fields.CharField',
        {
            'disabled': True,
            'widget': 'django.forms.PasswordInput',
            'required': False,
            'widget_kwargs': {'render_value': True},
        },
    ),
    'read_only': (
        'django.forms.fields.CharField',
        {'disabled': True, 'required': False},
    ),
    'read_only_bool': (
        'django.forms.fields.BooleanField',
        {'disabled': True, 'required': False},
    ),
    'read_only_int': (
        'django.forms.fields.IntegerField',
        {'disabled': True, 'required': False},
    ),
}

CONSTANCE_CONFIG = {
    'ICD_SYMPTOM_SIZE': (1, _('Size of icd symptom data'), int),
    'ICD_SYMPTOM_METRIC': ('angular', _('Annoy metric of icd symptom data'), 'one_line'),
    'MAXIMUM_NUMBER_OF_CLUSTERS': (30, _('Maximum number of clusters for grouping important features'), int),
    'PRIORITY_USERS': ('', _('Priority users (enter numbers separated by comma)'), 'one_line'),
    'MARK_PROTOCOLS_BATCH': (6, _('Number of protocols processed in parallel'), int),
    'LICENSE_SERVER_AUTH_BACKEND': (
        'https://lic.iambulant.ru:8000/auth_server/api/token/',
        _('License server auth url'),
        'one_line',
    ),
    'LICENSE_SERVER_LOGIN': (None, _('License server login'), 'one_line'),
    'LICENSE_SERVER_PASSWORD': (None, _('License server password'), 'password'),
    'LICENSE_ACCESS_TOKEN_LIFETIME': (86000, _('License access token lifetime, sec'), int),
    'LICENSE_REFRESH_TOKEN_LIFETIME': (431600, _('License refresh token lifetime, sec'), int),
}

# if you change keys in this fieldset, then you need change api.custom_admin.settings.enums
CONSTANCE_CONFIG_FIELDSETS = OrderedDict(
    [
        (
            'Настройки экосистемы',
            {
                'fields': (
                    'LICENSE_SERVER_AUTH_BACKEND',
                    'LICENSE_SERVER_LOGIN',
                    'LICENSE_SERVER_PASSWORD',
                    'LICENSE_ACCESS_TOKEN_LIFETIME',
                    'LICENSE_REFRESH_TOKEN_LIFETIME',
                ),
                'collapse': True,
            },
        ),
        (
            'Настройки обработки протоколов',
            {
                'fields': (
                    'ICD_SYMPTOM_SIZE',
                    'ICD_SYMPTOM_METRIC',
                    'PRIORITY_USERS',
                    'MARK_PROTOCOLS_BATCH',
                    'MAXIMUM_NUMBER_OF_CLUSTERS',
                ),
                'collapse': True,
            },
        ),
    ],
)

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# -------------------------------------- CACHEOPS -----------------------------------
CACHEOPS_REDIS = config('CACHEOPS_REDIS', default='redis://redis:6379/1')
CACHEOPS_DEFAULTS = {
    'timeout': 60 * 60,
}
# Models and operations to be cached
CACHEOPS = {
    'constance.config': {'ops': {'fetch', 'get'}},
    'secret_settings.ygpsettings': {'ops': {'fetch', 'get'}},
    'secret_settings.prompt': {'ops': {'fetch', 'get'}},
    'secret_settings.gigachatsettings': {'ops': {'fetch', 'get'}},
}
CACHEOPS_DEGRADE_ON_FAILURE = True

# ----------------------------------- DCF -------------------------------------
# django-crispy-forms
# https://github.com/django-crispy-forms/crispy-bootstrap5

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'

CRISPY_TEMPLATE_PACK = 'bootstrap5'

# -------------------------------------- SIMPLE JWT -----------------------------------
JWT_KEY_DIR = os.path.join(BASE_DIR, 'private', 'jwt_keys')
SIMPLE_JWT = {
    'ALGORITHM': 'RS256',
}
if os.path.isfile(os.path.join(JWT_KEY_DIR, 'jwt_key.pub')):
    with open(os.path.join(JWT_KEY_DIR, 'jwt_key.pub'), encoding='utf8') as file:
        SIMPLE_JWT['VERIFYING_KEY'] = file.read()

# -------------------------------------- NEURO BACKEND -----------------------------------
NEURO_USER_ID = config('NEURO_USER_ID', default=0, cast=int)
NEURO_BACKEND = config(
    'NEURO_BACKEND',
    default='https://neuro.iambulant.ru:8000',
)
LLM_TOKENIZER_DIR = os.path.join(BASE_DIR, 'private', 'llm', 'tokenizer')

# -------------------------------------- REQUESTS -----------------------------------
TIMEOUT_SHORT = config('TIMEOUT_SHORT', default=10, cast=int)
TIMEOUT_LONG = config('TIMEOUT_LONG', default=100, cast=int)

# -------------------------------------- SEMANTIC_SEARCH_DATA -----------------------------------
# ANNOY_DATA
ENTITIES_DATA_PATH = os.path.join(BASE_DIR, 'private', 'pkls', 'entities.pkl')
ENTITIES_NEODISEASE_DATA_PATH = os.path.join(BASE_DIR, 'private', 'pkls', 'entities_neodisease.pkl')
ANN_DATA_PATH = os.path.join(BASE_DIR, 'akcent_graph', 'utils', 'clients', 'gpt', 'anns')
ICD_SYMPTOM_DATA = os.path.join(BASE_DIR, 'private', 'pkls', 'full_description_au.pkl')
ICD_SYMPTOM_DATA_ANN = os.path.join(
    BASE_DIR,
    'akcent_graph',
    'utils',
    'clients',
    'gpt',
    'anns',
    'full_description_au.ann',
)
MERGE_ICD_SYMPTOM_DATA = os.path.join(
    BASE_DIR,
    'private',
    'pkls',
    'merge_full_description_au.pkl',
)
# ML_DEFAULT_VALUE
POSITIVE_FEATURE_BOUNDARY = config(
    'POSITIVE_FEATURE_BOUNDARY',
    default=0.36,
    cast=float,
)
POSITIVE_FEATURE_BOUNDARY_FOR_SINGLE_NODE = config(
    'POSITIVE_FEATURE_BOUNDARY_FOR_SINGLE_NODE',
    default=0.3,
    cast=float,
)
NEGATIVE_FEATURE_BOUNDARY = config(
    'NEGATIVE_FEATURE_BOUNDARY',
    default=0.48,
    cast=float,
)
DELTA_ONE_ADDITIONAL_FEATURE = config(
    'DELTA_ADDITIONAL_FEATURE',
    default=0.06,
    cast=float,
)
DELTA_SEVERAL_ADDITIONAL_FEATURE = config(
    'DELTA_ADDITIONAL_FEATURE',
    default=0.01,
    cast=float,
)
THRESHOLD_ANAMNESIS_FEATURE = config(
    'THRESHOLD_ANAMNESIS_FEATURE',
    default=0.41,
    cast=float,
)
EMBEDDER_FOR_GROUPING = config(
    'EMBEDDER_FOR_GROUPING',
    default='GigaChat',
)

# ---------------------------- FIND_PATHS_IN_GRAPHDB --------------------------
CHAIN_SEPARATOR = '$iamb$'
