import os
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any

import dj_database_url
from corsheaders.defaults import default_headers
from decouple import Csv, config
from django.utils.translation import gettext_lazy as _
from kombu import Queue

from ai_photoenhancer.utils.storage_tools import StorageType

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_DIR = os.path.join(BASE_DIR, 'ai_photoenhancer')

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
    'crispy_forms',
    'crispy_bootstrap5',
]

LOCAL_APPS = [
    'ai_photoenhancer.apps.common',
    'ai_photoenhancer.apps.background_remover',
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

ROOT_URLCONF = 'ai_photoenhancer.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'ai_photoenhancer/templates')],
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

WSGI_APPLICATION = 'ai_photoenhancer.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASE_URL = config('DATABASE_URL', default='postgres://postgres:postgres@db:5432/ai_photoenhancer')

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

HOST_IP_ADDRESS = config('HOST_IP_ADDRESS', default='http://127.0.0.1') or 'http://127.0.0.1'
HOSTNAME = config('AI_PHOTOENHANCER_HOSTNAME', default=HOST_IP_ADDRESS) or HOST_IP_ADDRESS
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
        'filename': log_dir / 'ai_photoenhancer.log',
        'class': 'logging.handlers.RotatingFileHandler',
        'maxBytes': 1024 * LOG_FILE_SIZE,
        'backupCount': 10,
        'formatter': 'default',
    }

# ---------------------------------- CELERY -----------------------------------
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TIMEZONE = TIME_ZONE
CELERYD_HIJACK_ROOT_LOGGER = False
CELERY_DEFAULT_QUEUE = 'default'
CELERY_TASK_DEFAULT_QUEUE = 'default'

CELERY_QUEUES = (Queue('default', routing_key='default'),)
CELERY_TASK_QUEUES = (Queue('default'),)
FAILED_TASK_RETRY_COUNTDOWN = config('FAILED_TASK_RETRY_COUNTDOWN', default=600, cast=int)

# ------------------------------ CUSTOM SETTINGS ------------------------------
PRODUCT_TITLE = _('Akcent ai photoenhancer')
PRODUCT_VERSION = config('PRODUCT_VERSION', default='dev version')
APPLICATION_UID = config('APPLICATION_UID', None)
LICENSE_CHECK_URL = config('LICENSE_CHECK_URL', default='https://lic.akcent.tech:8000/auth_server/check_license/')
LICENSE_SUCCESSFUL_CHECK_TIMEOUT = config('LICENSE_SUCCESSFUL_CHECK_TIMEOUT', cast=int, default=24 * 60 * 60)
LICENSE_FAILED_CHECK_TIMEOUT = config('LICENSE_FAILED_CHECK_TIMEOUT', cast=int, default=300)
UPLOAD_LINK_LIFETIME = config('UPLOAD_LINK_LIFETIME', cast=int, default=120)  # seconds
PROCESSED_IMAGES_STORE_TIME = config('PROCESSED_IMAGES_STORE_TIME', cast=int, default=2)  # hours
RETURNED_IMAGES_STORE_TIME = config('RETURNED_IMAGES_STORE_TIME', cast=int, default=1)  # hours

# ------------------------------- REST FRAMEWORK ------------------------------
REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'ai_photoenhancer.apps.common.authentication.CustomJWTStatelessUserAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

CORS_ALLOW_CREDENTIALS = True
CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_HEADERS = list(default_headers) + []

# -------------------------------- CONSTANCE ----------------------------------
CONSTANCE_BACKEND = 'ai_photoenhancer.utils.constance.DatabaseBackend'

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
    'storage_type': (
        'django.forms.fields.ChoiceField',
        {
            'widget': 'django.forms.Select',
            'choices': StorageType.choices,
            'required': False,
        },
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
    'STORAGE_TYPE': (None, _('File storage type'), 'storage_type'),
    'STORAGE_HOST': (None, _('File storage host'), 'one_line'),
    'STORAGE_NAME': (None, _('File storage name (bucket, etc.)'), 'one_line'),
    'STORAGE_LOGIN': (None, _('Username (key, id, etc.)'), 'one_line'),
    'STORAGE_PASSWORD': (None, _('Password (secret key, token, etc.)'), 'password'),
    'STORAGE_LOCATION': (None, _('Region name or similar'), 'one_line'),
    'EXAMPLES_PATH': (None, _('Path to original photo'), 'one_line'),
    'RESULTS_PATH': (None, _('Path to final photo'), 'one_line'),
    'RESULT_FILENAME_POSTFIX': (None, _('Result filename postfix'), 'one_line'),
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
            'Настройки хранилища',
            {
                'fields': (
                    'STORAGE_TYPE',
                    'STORAGE_HOST',
                    'STORAGE_NAME',
                    'STORAGE_LOGIN',
                    'STORAGE_PASSWORD',
                    'STORAGE_LOCATION',
                    'EXAMPLES_PATH',
                    'RESULTS_PATH',
                    'RESULT_FILENAME_POSTFIX',
                ),
                'collapse': True,
            },
        ),
    ],
)

# -------------------------------------- EMAIL -----------------------------------
EMAIL_BACKEND = config('EMAIL_BACKEND', None) or 'ai_photoenhancer.utils.email.ConstanceEmailBackend'
EMAIL_SUBJECT_PREFIX = '[Akcent] '

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

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

# -------------------------------------- REQUESTS -----------------------------------
TIMEOUT_SHORT = config('TIMEOUT_SHORT', default=10, cast=int)
TIMEOUT_LONG = config('TIMEOUT_LONG', default=100, cast=int)
