import os
from typing import Any

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from akcent_graph.apps.common.models import User
from akcent_graph.apps.medaggregator.tasks import prepare_graphdb_structure_with_parents


@pytest.fixture
@pytest.mark.django_db
def set_test_structure(request):
    request.cls.user = User.objects.create_user(username='testuser', password='12345')
    token = str(RefreshToken.for_user(request.cls.user).access_token)
    request.cls.headers = {'Authorization': f'Bearer {token}'}

    request.cls.structure = {
        'NeoOrgan': [
            'щитовидная железа',
            'печень',
            'почки',
            'селезенка',
            'сердце',
            'трахея',
            'щитовидная железа',
        ],
        'NeoDisease': [
            'мигрень',
            'отит',
            'атеросклероз сосудов',
            'ангина',
            'сахар',
        ],
        'NeoBodyStructure': [
            'орган',
            'структура',
        ],
    }


@pytest.mark.usefixtures('set_test_structure')
@pytest.mark.django_db
class TestGetGraphDBStructure:
    def test_get_structure_not_neuro_user(self, client: APIClient, mocker: Any, settings: Any):
        settings.NEURO_USER_ID = 'qwerty'
        mock_cache = mocker.patch('django.core.cache.cache.get')
        mock_cache.return_value = True
        response = client.get(
            reverse('medaggregator:get_structure'),
            headers=self.headers,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_structure_no_file(self, client: APIClient, mocker: Any, settings: Any):
        settings.NEURO_USER_ID = self.user.pk
        settings.GRAPHDB_STRUCTURE_JSON = os.path.join('private', 'test_graphdb_structure.json')
        mock_cache = mocker.patch('django.core.cache.cache.get')
        mock_cache.return_value = True
        mock_neo4jcrud = mocker.patch('akcent_graph.utils.neo.crud_operator.Neo4jCRUD.get_all_entities_by_class_names')
        mock_neo4jcrud.return_value = self.structure

        response = client.get(
            reverse('medaggregator:get_structure'),
            headers=self.headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_structure_ok(self, client: APIClient, mocker: Any, settings: Any):
        settings.NEURO_USER_ID = self.user.pk
        settings.GRAPHDB_STRUCTURE_JSON = os.path.join('private', 'test_graphdb_structure.json')
        mock_cache = mocker.patch('django.core.cache.cache.get')
        mock_cache.return_value = True
        mock_neo4jcrud = mocker.patch('akcent_graph.utils.neo.crud_operator.Neo4jCRUD.get_all_entities_by_class_names')
        mock_neo4jcrud.return_value = self.structure

        os.makedirs('private', exist_ok=True)
        prepare_graphdb_structure_with_parents()

        response = client.get(
            reverse('medaggregator:get_structure'),
            headers=self.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == self.structure

        os.remove(settings.GRAPHDB_STRUCTURE_JSON)
