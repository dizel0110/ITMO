# mypy: disable-error-code="index"
import os
import sys
from collections import OrderedDict
from pathlib import Path

import dj_database_url
import sentry_sdk
from corsheaders.defaults import default_headers
from decouple import Csv, config
from django.utils.translation import gettext_lazy as _
from sentry_sdk.integrations.django import DjangoIntegration

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_DIR = os.path.join(BASE_DIR, 'nlp')

DATA_UPLOAD_MAX_MEMORY_SIZE = None

sys.path.append(PROJECT_DIR)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config(
    'SECRET_KEY',
    default='django-insecure-uuq8m4)-r^os6+56qc24v$qu5c(ibn)@i2#1t3nnhyqxj9n-o0',
)

# SECURITY WARNING: don't run with debug turned on in production!
ENV = config('ENV', default='production')
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = []
AUTH_USER_MODEL = 'common.User'

GLOBAL_CLEANER = config('GLOBAL_CLEANER', cast=bool, default=False)

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
    'django_redis',
    'cacheops',
    'health_check',
    'health_check.db',
    'health_check.cache',
    'health_check.storage',
    'health_check.contrib.migrations',
    'health_check.contrib.celery',  # requires celery
    'health_check.contrib.celery_ping',  # requires celery
    'health_check.contrib.redis',
]

LOCAL_APPS = [
    'nlp.apps.common',
    'nlp.apps.protocol',
    'nlp.apps.secret_settings',
    'nlp.utils.LLM',
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
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'nlp.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'nlp/templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'nlp.apps.common.context_processors.akcent_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'nlp.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASE_URL = config('DATABASE_URL', default='postgres://postgres:postgres@db:5432/nlp')

DATABASES = {'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)}

REDIS_URL = config('REDIS_URL', default='redis://redis:6379/0')

DATA_UPLOAD_MAX_NUMBER_FIELDS = 100000


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

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


# ------------------------------- I18N & L10n ---------------------------------
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


# ------------------------------- FILE SYSTEM ---------------------------------
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

FORCE_SCRIPT_NAME = config('FORCE_SCRIPT_NAME', None)

HOST_IP_ADDRESS = config('HOST_IP_ADDRESS', default='http://127.0.0.1') or 'http://127.0.0.1'
HOSTNAME = config('NLP_HOSTNAME', default=HOST_IP_ADDRESS) or HOST_IP_ADDRESS
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

LOGGING = {
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
        'filename': log_dir / 'nlp.log',
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
CELERY_DEFAULT_EXCHANGE = 'default'
CELERY_DEFAULT_ROUTING_KEY = 'default'
CELERY_TASK_SOFT_TIME_LIMIT = 30 * 60
CELERY_TASK_TIME_LIMIT = 35 * 60
CELERY_TASK_QUEUES = {
    'high': {
        'binding_key': 'high',
    },
    'default': {
        'binding_key': 'default',
    },
    'low': {
        'binding_key': 'low',
    },
}

# ------------------------------ CUSTOM SETTINGS ------------------------------
PRODUCT_TITLE = _('Akcent AI Module')
PRODUCT_VERSION = config('PRODUCT_VERSION', default='dev version')
APPLICATION_UID = config('APPLICATION_UID', None)
PROCESSED_PROTOCOLS_STORE_TIME = config('PROCESSED_PROTOCOLS_STORE_TIME', default=60 * 24)  # minutes
LICENSE_CHECK_URL = config('LICENSE_CHECK_URL', default='https://lic.iambulant.ru:8000/auth_server/check_license/')
LICENSE_SUCCESSFUL_CHECK_TIMEOUT = config('LICENSE_SUCCESSFUL_CHECK_TIMEOUT', default=24 * 60 * 60)
LICENSE_FAILED_CHECK_TIMEOUT = config('LICENSE_FAILED_CHECK_TIMEOUT', default=300)

# ------------------------------- REST FRAMEWORK ------------------------------
REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_AUTHENTICATION_CLASSES': ('nlp.apps.common.authentication.CustomJWTStatelessUserAuthentication',),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

CORS_ALLOW_CREDENTIALS = True
CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_HEADERS = list(default_headers) + []

# -------------------------------- CONSTANCE ----------------------------------
CONSTANCE_BACKEND = 'nlp.utils.constance.DatabaseBackend'

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
    'EMAIL_HOST': ('localhost', _('The host to use for sending email.'), 'one_line'),
    'EMAIL_PORT': (25, _('Port to use for the SMTP server.'), int),
    'EMAIL_FROM': ('example@example.com', _('Email from address'), 'one_line'),
    'EMAIL_HOST_USER': (
        'webmaster',
        _('Username to use for the SMTP server.'),
        'one_line',
    ),
    'EMAIL_HOST_PASSWORD': ('', _('Password to use for the SMTP server.'), 'password'),
    'EMAIL_USE_TLS': (
        False,
        _(
            'Whether to use a TLS (secure) connection when talking to the SMTP server. '
            'This is used for explicit TLS connections, generally on port 587. If you are '
            'experiencing hanging connections, see the implicit TLS '
            'setting EMAIL_USE_SSL.',
        ),
        bool,
    ),
    'EMAIL_USE_SSL': (
        False,
        _(
            'Whether to use an implicit TLS (secure) connection when talking to the SMTP server. '
            'In most email documentation this type of TLS connection is referred to as SSL. '
            'It is generally used on port 465. If you are experiencing problems, '
            'see the explicit TLS setting EMAIL_USE_TLS.',
        ),
        bool,
    ),
    'EMAIL_SUPPORT': ('support@localhost', _('Default support mailbox.'), 'one_line'),
    'LICENSE_SERVER_AUTH_BACKEND': (
        'https://lic.iambulant.ru:8000/auth_server/api/token/',
        _('License server auth url'),
        'one_line',
    ),
    'LICENSE_SERVER_LOGIN': (None, _('License server login'), 'one_line'),
    'LICENSE_SERVER_PASSWORD': (None, _('License server password'), 'password'),
    'LICENSE_ACCESS_TOKEN_LIFETIME': (86000, _('License access token lifetime, sec'), int),
    'LICENSE_REFRESH_TOKEN_LIFETIME': (431600, _('License refresh token lifetime, sec'), int),
    'MAX_PARSING_ERRORS': (3, _('Maximum retries for parsing errors (0 for unlimited)'), int),
    'MAX_API_ERRORS': (10, _('Maximum retries for API errors (0 for unlimited)'), int),
    'BATCH_SIZE': (
        14,
        _('Batch size for multiprocess protocols. Stop and resume main process in Protocols section to apply changes'),
        int,
    ),
    'EMBEDDINGS_BATCH_SIZE': (
        14,
        _('Batch size for multiprocess embeddings'),
        int,
    ),
    'PRIORITY_USERS': ('', _('Priority users (enter numbers separated by comma)'), 'one_line'),
}

# if you change keys in this fieldset, then you need change api.custom_admin.settings.enums
CONSTANCE_CONFIG_FIELDSETS = OrderedDict(
    [
        (
            'Настройки электронной почты',
            {
                'fields': (
                    'EMAIL_HOST',
                    'EMAIL_PORT',
                    'EMAIL_FROM',
                    'EMAIL_HOST_USER',
                    'EMAIL_HOST_PASSWORD',
                    'EMAIL_USE_TLS',
                    'EMAIL_USE_SSL',
                    'EMAIL_SUPPORT',
                ),
                'collapse': True,
            },
        ),
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
                    'BATCH_SIZE',
                    'EMBEDDINGS_BATCH_SIZE',
                    'MAX_PARSING_ERRORS',
                    'MAX_API_ERRORS',
                    'PRIORITY_USERS',
                ),
                'collapse': True,
            },
        ),
    ],
)

# -------------------------------------- EMAIL -----------------------------------
EMAIL_BACKEND = config('EMAIL_BACKEND', None) or 'nlp.utils.email.ConstanceEmailBackend'
EMAIL_SUBJECT_PREFIX = '[Akcent] '

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# -------------------------------------- SIMPLE JWT -----------------------------------
JWT_KEY_DIR = os.path.join(BASE_DIR, 'private', 'jwt_keys')
SIMPLE_JWT = {
    'ALGORITHM': 'RS256',
}
if os.path.isfile(os.path.join(JWT_KEY_DIR, 'jwt_key.pub')):
    with open(os.path.join(JWT_KEY_DIR, 'jwt_key.pub'), encoding='utf8') as file:
        SIMPLE_JWT['VERIFYING_KEY'] = file.read()

# -------------------------------------- CACHEOPS -----------------------------------
CACHEOPS_REDIS = config('CACHEOPS_REDIS', default='redis://redis:6379/1')
CACHEOPS_DEFAULTS = {
    'timeout': 60 * 60,
}
# Models and operations to be cached
CACHEOPS = {
    'constance.config': {'ops': {'fetch', 'get'}},
    'common.user': {'ops': {'fetch', 'get'}},
}
CACHEOPS_DEGRADE_ON_FAILURE = True

# -------------------------------------- LLM -----------------------------------
LLM_SERVICE_URL = config('LLM_SERVICE_URL', default='http://llm_service:8001')
EMBEDDER_SERVICE_URL = config('EMBEDDER_SERVICE_URL', default='http://llm_service:8002')
LLM_TOKENIZER_DIR = os.path.join(BASE_DIR, 'models', 'Vikhr')

ANNOY_DATA_PATH = os.path.join(BASE_DIR, 'private', 'pkls', 'entities.pkl')
# -------------------------------------- REQUESTS -----------------------------------
TIMEOUT_SHORT = config('TIMEOUT_SHORT', default=10, cast=int)
TIMEOUT_LONG = config('TIMEOUT_LONG', default=100, cast=int)

# ------------------------------------- CACHE --------------------------------------
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
    },
}

# __________________________________________GRAPHDB_PROTOCOL_BACKEND___________________________________
GRAPHDB_PROTOCOL_BACKEND = config(
    'GRAPHDB_PROTOCOL_BACKEND',
    default='https://graph.iambulant.ru:8000',
)
DATA_STRUCTURE_CHECK_TIMEOUT = config('DATA_STRUCTURE_CHECK_TIMEOUT', default=86400, cast=int)
