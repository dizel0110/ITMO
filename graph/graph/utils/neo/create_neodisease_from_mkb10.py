from neomodel import DoesNotExist

from akcent_graph.apps.medaggregator.models import NeoDisease, NeoMkb10_level_04, NeoMkb10_level_05, NeoMkb10_level_06

neomkb10_level_04 = NeoMkb10_level_04.nodes.all()
neomkb10_level_05 = NeoMkb10_level_05.nodes.all()
neomkb10_level_06 = NeoMkb10_level_06.nodes.all()

for entity in neomkb10_level_04:
    NeoDisease.get_or_create({'name': entity.name, 'treecode': entity.treecode, 'level': entity.level})
    try:
        node_disease = NeoDisease.nodes.get(treecode=entity.treecode)
        if node_disease:
            entity.to_disease.connect(node_disease, {})
            node_disease.to_neomkb10_level_04.connect(entity)
    except DoesNotExist:
        pass

for entity in neomkb10_level_05:
    NeoDisease.get_or_create({'name': entity.name, 'treecode': entity.treecode, 'level': entity.level})
    try:
        node_disease = NeoDisease.nodes.get(treecode=entity.treecode)
        if node_disease:
            entity.to_disease.connect(node_disease, {})
            node_disease.to_neomkb10_level_05.connect(entity)
    except DoesNotExist:
        pass

for entity in neomkb10_level_06:
    NeoDisease.get_or_create({'name': entity.name, 'treecode': entity.treecode, 'level': entity.level})
    try:
        node_disease = NeoDisease.nodes.get(treecode=entity.treecode)
        if node_disease:
            entity.to_disease.connect(node_disease, {})
            node_disease.to_neomkb10_level_06.connect(entity)
    except DoesNotExist:
        pass
