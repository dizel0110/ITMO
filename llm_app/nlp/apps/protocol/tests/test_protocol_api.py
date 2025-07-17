# pylint: disable=no-member
from typing import Any, Optional

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from nlp.apps.common.models import User
from nlp.apps.protocol.models import Protocol


@pytest.fixture
@pytest.mark.django_db
def prepare_user_token(request):
    request.cls.user = User.objects.create_user(username='testuser', password='12345')
    token = str(RefreshToken.for_user(request.cls.user).access_token)
    request.cls.headers = {'Authorization': f'Bearer {token}'}


@pytest.mark.usefixtures('prepare_user_token')
@pytest.mark.django_db
class TestProtocolAPI:
    def test_protocol_unauthorized(self, client: APIClient):
        response = client.post(
            reverse('protocol:protocol'),
            {'medcard_id': 1212, 'raw_text': 'text'},
            format='json',
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        'payload,status_code,medcard_id,service_id',
        [
            ({'medcard_id': 1212, 'raw_text': 'text'}, status.HTTP_201_CREATED, '1212', None),
            ({'medcard_id': 1212, 'raw_text': 'text', 'service_id': 123}, status.HTTP_201_CREATED, '1212', 123),
            ({'medcard_id': 1212, 'service_id': 123}, status.HTTP_400_BAD_REQUEST, None, None),
            ({'raw_text': 'text', 'service_id': 123}, status.HTTP_201_CREATED, '', 123),
        ],
    )
    def test_create_protocol(
        self,
        client: APIClient,
        mocker: Any,
        payload: dict[str, Any],
        status_code: int,
        medcard_id: str,
        service_id: Optional[int],
    ) -> None:
        mock_cache = mocker.patch('django.core.cache.cache.get')
        mock_cache.return_value = True
        response = client.post(reverse('protocol:protocol'), payload, format='json', headers=self.headers)
        assert response.status_code == status_code
        if status_code != status.HTTP_201_CREATED:
            return
        json_sesponse = response.json()
        assert json_sesponse.get('medcard_id') == medcard_id
        assert json_sesponse.get('user_id') == str(self.user.id)
        assert json_sesponse.get('service_id') == service_id

    def test_get_protocols(self, client: APIClient, mocker: Any):
        mock_cache = mocker.patch('django.core.cache.cache.get')
        mock_cache.return_value = True
        id1 = Protocol.objects.create(medcard_id=1212, user_id=self.user.id, raw_text='text').id
        id2 = Protocol.objects.create(medcard_id=1212, user_id=self.user.id, raw_text='text', service_id=123).id
        Protocol.objects.create(medcard_id=1213, user_id=self.user.id, raw_text='text', service_id=123)
        Protocol.objects.create(medcard_id=1212, user_id='qwe', raw_text='text', service_id=123)
        Protocol.objects.create(medcard_id=1213, user_id='qwe', raw_text='text', service_id=123)

        params = {'medcard_id': '1212'}
        response = client.get(
            reverse('protocol:protocol'),
            data=params,
            headers=self.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

        Protocol.objects.all().update(processed_at='2024-08-01T00:00:00+00:00')

        response = client.get(
            reverse('protocol:protocol'),
            data=params,
            headers=self.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == [
            {
                'id': id1,
                'service_id': None,
                'result': None,
            },
            {
                'id': id2,
                'service_id': 123,
                'result': None,
            },
        ]

        params = {'medcard_id': '1212', 'service_id': 123}
        response = client.get(
            reverse('protocol:protocol'),
            data=params,
            headers=self.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == [
            {
                'id': id2,
                'service_id': 123,
                'result': None,
            },
        ]
