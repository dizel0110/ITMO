from typing import Any

import pytest

from akcent_graph.apps.common.ext_webservice_adapters import NeuroAdapter


@pytest.mark.django_db
class TestNeuroAdapter:
    def test_embed_query(self, mocker: Any):
        mock_cache = mocker.patch('django.core.cache.cache.get')
        mock_cache.return_value = 'token'
        mock_response = mocker.patch('requests.Session.send')
        mock_response.return_value.json.return_value = ['embedding']
        adapter = NeuroAdapter()
        embedding = adapter.embed_query('qwerty')
        assert embedding == ['embedding']
        assert mock_response.call_count == 1
        assert mock_cache.call_count == 1
