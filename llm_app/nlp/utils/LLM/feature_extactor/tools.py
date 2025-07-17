from typing import Any

from django.core.cache import cache

from nlp.apps.secret_settings.models import DBStructure


async def async_get_graphdb_structure() -> dict[str, Any]:
    structure = await cache.aget('graphdb_structure')
    if not structure:
        structure_entry = await DBStructure.objects.aget(name='entities')
        structure = structure_entry.structure
        await cache.aset('graphdb_structure', structure)
    return structure
