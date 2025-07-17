import logging

import requests
from django.core.cache import cache

from nlp.apps.common.ext_webservice_adapters import GraphDBAdapter
from nlp.apps.secret_settings.models import DBStructure
from nlp.celeryapp import app

logger = logging.getLogger(__name__)


@app.task(ignore_results=True)
def refresh_graphdb_structure() -> None:
    adapter = GraphDBAdapter()
    if not adapter.is_ready:
        logger.warning('Connection adapter not ready!')
        return
    try:
        structure = adapter.get_structure()
        if not structure:
            return
    except requests.exceptions.RequestException as exc:
        logger.error('GraphDB structure fetch failed:', exc_info=exc)
        return

    index = 1
    for class_name, features in structure.items():
        new_features = []
        for feature in features:
            new_features.append(
                {
                    'name': feature,
                    'index': index,
                    'parents': [],
                },
            )
            index += 1
        structure[class_name] = new_features

    structure_entry, __ = DBStructure.objects.get_or_create(name='entities', defaults={'structure': {}})
    structure_entry.structure = structure
    structure_entry.save()
    cache.set('graphdb_structure', structure)
