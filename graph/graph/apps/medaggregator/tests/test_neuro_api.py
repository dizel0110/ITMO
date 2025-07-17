from copy import deepcopy
from typing import Any

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from akcent_graph.apps.common.models import User


@pytest.fixture
@pytest.mark.django_db
def prepare_user_token(request):
    request.cls.user = User.objects.create_user(username='testuser', password='12345')
    token = str(RefreshToken.for_user(request.cls.user).access_token)
    request.cls.headers = {'Authorization': f'Bearer {token}'}


@pytest.fixture
def prepare_test_data(request):
    request.cls.test_protocol_data = {
        'medcard_id': 'medcard-id',
        'user_id': 'user-id',
        'protocol_custom_id': 'qwerty',
        'service_id': 123,
        'is_medtest': False,
        'protocol_data': [
            {
                'name': 'лекарство',
                'class': 'NeoMedServiceFeature',
                'index': 1,
                'value': None,
                'parents': [],
                'index_bd': None,
            },
            {
                'name': 'тонзиллит',
                'class': 'NeoDisease',
                'index': 1,
                'value': None,
                'parents': [],
                'index_bd': 1,
            },
        ],
    }


@pytest.mark.usefixtures('prepare_user_token', 'prepare_test_data')
@pytest.mark.django_db
class TestNeuroAPI:
    def test_load_protocol_unauthorized(self, client: APIClient):
        response = client.post(
            reverse('medaggregator:upload_protocol'),
            self.test_protocol_data,
            format='json',
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_load_protocol_not_neuro_user(self, client: APIClient, mocker: Any, settings: Any):
        settings.NEURO_USER_ID = 'qwerty'
        mock_cache = mocker.patch('django.core.cache.cache.get')
        mock_cache.return_value = True
        response = client.post(
            reverse('medaggregator:upload_protocol'),
            self.test_protocol_data,
            format='json',
            headers=self.headers,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_load_protocol_wrong_structure(self, client: APIClient, mocker: Any, settings: Any):
        settings.NEURO_USER_ID = self.user.pk
        mock_cache = mocker.patch('django.core.cache.cache.get')
        mock_cache.side_effect = [
            True,
        ]
        wrong_protocol = self.test_protocol_data.copy()
        wrong_protocol['protocol_data'].append(
            {
                'name': '3 р.д.',
                'class': 'NeoMedServiceFeatureValue',
                'index': 1,
                'value': None,
                'parents': [],
                'index_bd': None,
            },
        )
        wrong_protocol['protocol_data'].append(
            {
                'name': '3 р.д.',
                'index': 1,
                'value': None,
                'parents': [],
                'index_bd': None,
            },
        )
        response = client.post(
            reverse('medaggregator:upload_protocol'),
            self.test_protocol_data,
            format='json',
            headers=self.headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == [
            {
                'entry': {
                    'name': '3 р.д.',
                    'class': 'NeoMedServiceFeatureValue',
                    'index': 1,
                    'value': None,
                    'parents': [],
                    'index_bd': None,
                },
                'error': 'Unknown class name: NeoMedServiceFeatureValue',
            },
            {
                'entry': {
                    'name': '3 р.д.',
                    'index': 1,
                    'value': None,
                    'parents': [],
                    'index_bd': None,
                },
                'error': '`class` key is missing',
            },
        ]

    def test_load_protocol_ok(self, client: APIClient, mocker: Any, settings: Any):
        settings.NEURO_USER_ID = self.user.pk
        mock_cache = mocker.patch('django.core.cache.cache.get')
        mock_cache.side_effect = [
            True,
            True,
        ]
        response = client.post(
            reverse('medaggregator:upload_protocol'),
            self.test_protocol_data,
            format='json',
            headers=self.headers,
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json() == []

        response = client.get(
            reverse('medaggregator:get_protocol', args=(self.test_protocol_data['protocol_custom_id'],)),
            headers=self.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == self.test_protocol_data

    def test_load_protocol_warning(self, client: APIClient, mocker: Any, settings: Any):
        settings.NEURO_USER_ID = self.user.pk
        mock_cache = mocker.patch('django.core.cache.cache.get')
        mock_cache.side_effect = [
            True,
            True,
        ]
        payload = deepcopy(self.test_protocol_data)
        payload['protocol_data'].append(
            {
                'name': '1',
                'class': 'NeoProtocol',
                'index': 1,
                'value': None,
                'parents': [],
                'index_bd': 1,
            },
        )
        response = client.post(
            reverse('medaggregator:upload_protocol'),
            payload,
            format='json',
            headers=self.headers,
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json() == [
            {
                'entry': {
                    'name': '1',
                    'class': 'NeoProtocol',
                    'index': 1,
                    'value': None,
                    'parents': [],
                    'index_bd': 1,
                },
                'error': 'Redundant classes: NeoPatient/NeoProtocol',
            },
        ]

        response = client.get(
            reverse('medaggregator:get_protocol', args=(self.test_protocol_data['protocol_custom_id'],)),
            headers=self.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == self.test_protocol_data

    def test_delete_test_protocol_task_run(self, client: APIClient, mocker: Any, settings: Any):
        settings.NEURO_USER_ID = self.user.pk
        mock_task = mocker.patch('akcent_graph.apps.medaggregator.tasks.delete_test_protocol.apply_async')
        mock_cache = mocker.patch('django.core.cache.cache.get')
        mock_cache.side_effect = [
            True,
            True,
        ]
        payload = {
            'medcard_id': 'medcard-id',
            'user_id': 'user-id',
            'protocol_custom_id': 'qwerty',
            'service_id': 123,
            'is_medtest': False,
            'protocol_data': [
                {
                    'name': '269a0e7a-82b1-4cd0-9013-8098f9cbd4c0',
                    'class': 'NeoMedServiceFeature',
                    'index': 1,
                    'value': None,
                    'parents': [],
                    'index_bd': None,
                },
            ],
        }
        response = client.post(
            reverse('medaggregator:upload_protocol'),
            payload,
            format='json',
            headers=self.headers,
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json() == []

        response = client.get(
            reverse('medaggregator:get_protocol', args=('qwerty',)),
            headers=self.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == payload
        mock_task.assert_called_once()
