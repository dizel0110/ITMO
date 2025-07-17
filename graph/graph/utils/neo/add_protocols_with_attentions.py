import json

from akcent_graph.utils.neo.crud_operator import Neo4jCRUD

neo4jcrud = Neo4jCRUD()

with open('akcent_graph/utils/neo/data/fixtures_of_protocols/class_sequence_number.json', 'r') as json_file:
    class_sequence_number = json.load(json_file)

sequence_number_class = dict(zip(class_sequence_number.values(), class_sequence_number.keys()))

patient_pk = 5
protocol_pk = 234554

with open(
    f'akcent_graph/utils/neo/data/fixtures_of_protocols' f'/patient_{patient_pk}_protocol_{protocol_pk}.json',
    'r',
) as json_file:
    data_neuro_protocol = json.load(json_file)

final_data_neuro_protocol = []
for element in data_neuro_protocol:
    element['class'] = sequence_number_class[element['class']]
    final_data_neuro_protocol.append(element)

neo4jcrud.create_nodes_and_relationships(patient_pk, protocol_pk, final_data_neuro_protocol)

patient_pk = 7
protocol_pk = 235001

with open(
    f'akcent_graph/utils/neo/data/fixtures_of_protocols/patient_{patient_pk}_protocol_{protocol_pk}.json',
    'r',
) as json_file:
    data_neuro_protocol = json.load(json_file)

final_data_neuro_protocol = []
for element in data_neuro_protocol:
    element['class'] = sequence_number_class[element['class']]
    final_data_neuro_protocol.append(element)

neo4jcrud.create_nodes_and_relationships(patient_pk, protocol_pk, final_data_neuro_protocol)

patient_pk = 7
protocol_pk = 235002

with open(
    f'akcent_graph/utils/neo/data/fixtures_of_protocols/patient_{patient_pk}_protocol_{protocol_pk}.json',
    'r',
) as json_file:
    data_neuro_protocol = json.load(json_file)

final_data_neuro_protocol = []
for element in data_neuro_protocol:
    element['class'] = sequence_number_class[element['class']]
    final_data_neuro_protocol.append(element)

neo4jcrud.create_nodes_and_relationships(patient_pk, protocol_pk, final_data_neuro_protocol)

patient_pk = 7
protocol_pk = 235003

with open(
    f'akcent_graph/utils/neo/data/fixtures_of_protocols/patient_{patient_pk}_protocol_{protocol_pk}.json',
    'r',
) as json_file:
    data_neuro_protocol = json.load(json_file)

final_data_neuro_protocol = []
for element in data_neuro_protocol:
    element['class'] = sequence_number_class[element['class']]
    final_data_neuro_protocol.append(element)

neo4jcrud.create_nodes_and_relationships(patient_pk, protocol_pk, final_data_neuro_protocol)

patient_pk = 7
protocol_pk = 235100

with open(
    f'akcent_graph/utils/neo/data/fixtures_of_protocols/patient_{patient_pk}_protocol_{protocol_pk}.json',
    'r',
) as json_file:
    data_neuro_protocol = json.load(json_file)

final_data_neuro_protocol = []
for element in data_neuro_protocol:
    element['class'] = sequence_number_class[element['class']]
    final_data_neuro_protocol.append(element)

neo4jcrud.create_nodes_and_relationships(patient_pk, protocol_pk, final_data_neuro_protocol)
