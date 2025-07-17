import uuid
from typing import Any

import pytest
import requests

from nlp.apps.protocol.models import Protocol, ProtocolStructureError
from nlp.apps.protocol.tasks import send_protocols_to_graphdb


class MockResponse201:
    status_code = 201

    def json(self):
        return []

    def raise_for_status(self):
        return


class MockResponse400:
    status_code = 400

    def json(self):
        return [{'entry': {}, 'error': 'error'}]

    def raise_for_status(self):
        raise requests.exceptions.RequestException


class MockResponse401:
    status_code = 401

    def raise_for_status(self):
        raise requests.exceptions.RequestException


@pytest.fixture
@pytest.mark.django_db
def create_protocols(request):
    for __ in range(5):
        Protocol.objects.create(
            medcard_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            raw_text='text',
            service_id=123,
            result={
                'name': str(uuid.uuid4()),
                'value': str(uuid.uuid4()),
            },
        )


@pytest.mark.django_db
class TestGraphDBAPI:
    @pytest.mark.usefixtures('create_protocols')
    def test_send_protocols_ok(self, mocker: Any):
        mock_cache = mocker.patch('django.core.cache.cache.get')
        mock_cache.side_effect = [True, 'token']
        mock_response = mocker.patch('requests.Session.send')
        mock_response.return_value = MockResponse201()
        send_protocols_to_graphdb()
        assert Protocol.objects.filter(is_sent_to_graphdb=True).count() == 5
        assert mock_response.call_count == 5
        assert mock_cache.call_count == 2

    @pytest.mark.usefixtures('create_protocols')
    def test_send_protocols_fail(self, mocker: Any):
        mock_cache = mocker.patch('django.core.cache.cache.get')
        mock_cache.side_effect = [True, 'token']
        mock_response = mocker.patch('requests.Session.send')
        mock_response.side_effect = [
            MockResponse201(),
            MockResponse201(),
            MockResponse400(),
            MockResponse401(),
        ]
        send_protocols_to_graphdb()
        assert Protocol.objects.filter(is_sent_to_graphdb=True).count() == 3
        assert mock_response.call_count == 4
        assert mock_cache.call_count == 2
        structure_error = ProtocolStructureError.objects.first()
        assert structure_error
        assert structure_error.errors == [{'entry': {}, 'error': 'error'}]

    def test_data_structure(self, mocker: Any):
        Protocol.objects.create(
            medcard_id='medcard-id',
            user_id='user-id',
            protocol_custom_id='qwerty',
            raw_text='text',
            service_id=123,
            result={
                'name': 'name-1',
                'value': 'value-1',
            },
        )
        mock_cache = mocker.patch('django.core.cache.cache.get')
        mock_cache.side_effect = [True, 'token']
        mock_response = mocker.patch('nlp.apps.common.ext_webservice_adapters.GraphDBAdapter._send_request')
        mock_response.return_value = MockResponse201()
        send_protocols_to_graphdb()
        assert mock_response.call_args.kwargs['json'] == {
            'medcard_id': 'medcard-id',
            'user_id': 'user-id',
            'protocol_custom_id': 'qwerty',
            'service_id': 123,
            'protocol_data': {'name': 'name-1', 'value': 'value-1'},
        }
