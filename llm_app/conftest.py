import os

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def override_django_setting(settings):
    settings.LANGUAGE_CODE = 'en-US'
    settings.LANGUAGES = (('en', 'English'),)
    with open(os.path.join('nlp', 'apps', 'common', 'tests', 'test_key.pem'), encoding='utf8') as file:
        settings.SIMPLE_JWT['SIGNING_KEY'] = file.read()
    with open(os.path.join('nlp', 'apps', 'common', 'tests', 'test_key.pub'), encoding='utf8') as file:
        settings.SIMPLE_JWT['VERIFYING_KEY'] = file.read()


@pytest.fixture(scope='session', autouse=True)
def clear_db_cache_after_tests():
    """Clears Cacheops db cache from cached test data"""

    yield
    call_command('invalidate', 'all')


@pytest.fixture
@pytest.mark.django_db
def client():
    client = APIClient()
    return client
