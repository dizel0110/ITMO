from neomodel import DoesNotExist

from akcent_graph.apps.medaggregator.models import (
    NeoAnatomicalFeature,
    NeoAnatomicalValue,
    NeoBodySystem,
    NeoDisease,
    NeoInspectionFeature,
    NeoInspectionValue,
    NeoMedServiceFeature,
    NeoMedServiceValue,
    NeoMkb10_level_01,
    NeoMkb10_level_02,
    NeoMkb10_level_03,
    NeoMkb10_level_04,
    NeoMkb10_level_05,
    NeoMkb10_level_06,
    NeoOrgan,
    NeoSymptomFeature,
    NeoSymptomValue,
    NeoTherapyFeature,
    NeoTherapyValue,
)
from akcent_graph.utils.neo.crud_operator import Neo4jCRUD
from akcent_graph.utils.neo.read_data import (
    anatomicalfeature_fixtures,
    anatomicalfeatureanatomicalvalue_fixtures,
    anatomicalvalue_fixtures,
    anomality_features,
    bodyfluids_features,
    bodysystem_fixtures,
    bodysystemorganrel_fixtures,
    inspectionfeature_fixtures,
    inspectionfeaturesinspectionvaluerel_fixtures,
    inspectionvalue_fixtures,
    med_service_feature_fixtures,
    med_service_features_values_fixtures,
    med_service_value_fixtures,
    mkb10_leveled,
    organ_fixtures,
    organstructure_fixtures,
    symptomfeature_fixtures,
    symptomfeaturessymptomvaluerel_fixtures,
    symptomvalue_fixtures,
    therapyfeature_fixtures,
    therapyfeaturessymptomvaluerel_fixtures,
    therapyvalue_fixtures,
)

neo4jcrud = Neo4jCRUD()

neo4jcrud.add_mkb10_graph(mkb10_leveled=mkb10_leveled)

for bodysystem in bodysystem_fixtures:
    NeoBodySystem.get_or_create({'name': bodysystem})

neomkb10_level_01 = NeoMkb10_level_01.nodes.all()
neomkb10_level_02 = NeoMkb10_level_02.nodes.all()
neomkb10_level_03 = NeoMkb10_level_03.nodes.all()
neomkb10_level_04 = NeoMkb10_level_04.nodes.all()
neomkb10_level_05 = NeoMkb10_level_05.nodes.all()
neomkb10_level_06 = NeoMkb10_level_06.nodes.all()

for entity in neomkb10_level_01:
    NeoDisease.get_or_create({'name': entity.name, 'treecode': entity.treecode, 'level': entity.level})
    try:
        node_disease = NeoDisease.nodes.get(treecode=entity.treecode)
        if node_disease:
            entity.to_disease.connect(node_disease, {})
            node_disease.to_neomkb10_level_01.connect(entity)
    except DoesNotExist:
        pass

for entity in neomkb10_level_02:
    NeoDisease.get_or_create({'name': entity.name, 'treecode': entity.treecode, 'level': entity.level})
    try:
        node_disease = NeoDisease.nodes.get(treecode=entity.treecode)
        if node_disease:
            entity.to_disease.connect(node_disease, {})
            node_disease.to_neomkb10_level_02.connect(entity)
    except DoesNotExist:
        pass

for entity in neomkb10_level_03:
    NeoDisease.get_or_create({'name': entity.name, 'treecode': entity.treecode, 'level': entity.level})
    try:
        node_disease = NeoDisease.nodes.get(treecode=entity.treecode)
        if node_disease:
            entity.to_disease.connect(node_disease, {})
            node_disease.to_neomkb10_level_03.connect(entity)
    except DoesNotExist:
        pass

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

for organ in organ_fixtures:
    neo4jcrud.createorganNode(
        name=organ,
    )

bodysystems = list(bodysystemorganrel_fixtures.keys())
for bodysystem in bodysystems:
    node_bodysystem = NeoBodySystem.get_or_create({'name': bodysystem})
    bodysystem_organs = bodysystemorganrel_fixtures.get(bodysystem)
    for organ in bodysystem_organs:
        node_organ = NeoOrgan.get_or_create({'name': organ})
        neo4jcrud.connect_nodes(node_bodysystem[0], node_organ[0])


for organstructure in organstructure_fixtures:
    neo4jcrud.createorganstructureNode(
        name=organstructure,
    )

for anatomicalfeature in anatomicalfeature_fixtures:
    neo4jcrud.createanatomicalfeatureNode(
        name=anatomicalfeature,
    )

for anatomicalvalue in anatomicalvalue_fixtures:
    neo4jcrud.createanatomicalvalueNode(
        name=anatomicalvalue,
    )

anatomicalfeatures = list(anatomicalfeatureanatomicalvalue_fixtures.keys())
for anatomicalfeature in anatomicalfeatures:
    node_anatomicalfeature = NeoAnatomicalFeature.get_or_create({'name': anatomicalfeature})
    anatomicalfeature_anatomicalvalues = anatomicalfeatureanatomicalvalue_fixtures.get(anatomicalfeature)
    for anatomicalvalue in anatomicalfeature_anatomicalvalues:
        node_anatomicalvalue = NeoAnatomicalValue.get_or_create({'name': anatomicalvalue})
        neo4jcrud.connect_nodes(node_anatomicalfeature[0], node_anatomicalvalue[0])

for anomality in anomality_features:
    neo4jcrud.createanomalityNode(
        name=anomality,
    )

for bodyfluids in bodyfluids_features:
    neo4jcrud.createbodyfluidsNode(
        name=bodyfluids,
    )

for symptomfeature in symptomfeature_fixtures:
    neo4jcrud.createsymptomfeatureNode(
        name=symptomfeature,
    )

for symptomvalue in symptomvalue_fixtures:
    neo4jcrud.createsymptomvalueNode(
        name=symptomvalue,
    )

symptomfeatures = list(symptomfeaturessymptomvaluerel_fixtures.keys())
for symptomfeature in symptomfeatures:
    node_symptomfeature = NeoSymptomFeature.get_or_create({'name': symptomfeature})
    symptomfeature_symptomvalues = symptomfeaturessymptomvaluerel_fixtures.get(symptomfeature)
    for symptomvalue in symptomfeature_symptomvalues:
        node_symptomvalue = NeoSymptomValue.get_or_create({'name': symptomvalue})
        neo4jcrud.connect_nodes(node_symptomfeature[0], node_symptomvalue[0])

for therapyfeature in therapyfeature_fixtures:
    neo4jcrud.createtherapyfeatureNode(
        name=therapyfeature,
    )

for therapyvalue in therapyvalue_fixtures:
    neo4jcrud.createtherapyvalueNode(
        name=therapyvalue,
    )

therapyfeatures = list(therapyfeaturessymptomvaluerel_fixtures.keys())
for therapyfeature in therapyfeatures:
    node_therapyfeature = NeoTherapyFeature.get_or_create({'name': therapyfeature})
    therapyfeature_therapyvalues = therapyfeaturessymptomvaluerel_fixtures.get(therapyfeature)
    for therapyvalue in therapyfeature_therapyvalues:
        node_therapyvalue = NeoTherapyValue.get_or_create({'name': therapyvalue})
        neo4jcrud.connect_nodes(node_therapyfeature[0], node_therapyvalue[0])

for inspectionfeature in inspectionfeature_fixtures:
    neo4jcrud.createtherapyfeatureNode(
        name=inspectionfeature,
    )

for inspectionvalue in inspectionvalue_fixtures:
    neo4jcrud.createtherapyvalueNode(
        name=inspectionvalue,
    )

inspectionfeatures = list(inspectionfeaturesinspectionvaluerel_fixtures.keys())
for inspectionfeature in inspectionfeatures:
    node_inspectionfeature = NeoInspectionFeature.get_or_create({'name': inspectionfeature})
    inspectionfeature_inspectionvalues = inspectionfeaturesinspectionvaluerel_fixtures.get(inspectionfeature)
    for inspectionvalue in inspectionfeature_inspectionvalues:
        node_inspectionvalue = NeoInspectionValue.get_or_create({'name': inspectionvalue})
        neo4jcrud.connect_nodes(node_inspectionfeature[0], node_inspectionvalue[0])

for med_service_feature in med_service_feature_fixtures:
    neo4jcrud.create_med_service_feature_node(
        name=med_service_feature,
    )

for med_service_value in med_service_value_fixtures:
    neo4jcrud.create_med_service_value_node(
        name=med_service_value,
    )

med_service_features = list(med_service_features_values_fixtures.keys())
for med_service_feature in med_service_features:
    med_service_feature_node = NeoMedServiceFeature.get_or_create({'name': med_service_feature})
    med_service_features_values = med_service_features_values_fixtures.get(med_service_feature)
    for med_service_value in med_service_features_values:
        med_service_value_node = NeoMedServiceValue.get_or_create({'name': med_service_value})
        neo4jcrud.connect_nodes(med_service_feature_node[0], med_service_value_node[0])
