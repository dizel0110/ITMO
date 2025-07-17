import os

import pytest

from django.core.management import call_command
from mixer.backend.django import mixer as _mixer
from rest_framework.test import APIClient


@pytest.fixture
def mixer():
    """The class Mixer for generate instances of different models."""
    return _mixer


@pytest.fixture(autouse=True)
def override_django_setting(settings):
    settings.LANGUAGE_CODE = 'en-US'
    settings.LANGUAGES = (('en', 'English'),)
    with open(os.path.join('akcent_graph', 'apps', 'common', 'tests', 'test_key.pem'), encoding='utf8') as file:
        settings.SIMPLE_JWT['SIGNING_KEY'] = file.read()
    with open(os.path.join('akcent_graph', 'apps', 'common', 'tests', 'test_key.pub'), encoding='utf8') as file:
        settings.SIMPLE_JWT['VERIFYING_KEY'] = file.read()


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command('loaddata', 'test_init/db_test.json')


@pytest.fixture
@pytest.mark.django_db
def client():
    client = APIClient()
    return client
