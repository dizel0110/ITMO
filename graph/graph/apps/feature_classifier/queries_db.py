"""
Module for cypher query of neo4j.
=================================

Classes:
----------
QueryMarkingFeatures

Dependencies:
-------------
enum

"""


import enum

from akcent_graph.apps.medaggregator.helpers import DataImportanceFeature


class QueryMarkingFeatures(enum.Enum):
    """
    Cypher query templates for feature classifier.
    ==============================================

    Variables:
    ----------
    FIRST_MARKING_QUERY\n
    ADDITIONAL_MARKING_QUERY\n
    CHANGE_ATTENTION_SCORE_RELATION\n
    CHANGE_ATTENTION_RELATION\n
    UNIQUE_ATTENTION_IN_PROTOCOL\n
    DISEASE_OF_PROTOCOL\n
    CONTAINS_CHAIN_ONE_PROTOCOL\n
    IS_CONNECTION_BETWEEN_NODES\n

    """

    FIRST_MARKING_QUERY = """MATCH (n)-[r:TO_PROTOCOL]-(m)
    WHERE n.name = {protocol.name} AND n.patient_id = {protocol.patient} AND labels(n) = ["NeoProtocol"] AND NOT labels(m) = ["NeoPatient"]
    RETURN labels(m)[0] AS class_parent_node, m.name AS name_parent_node, properties(r).value AS value_parent_node, properties(r).chain AS chain_parent_node
    """
    ADDITIONAL_MARKING_QUERY = f"""MATCH (n)-[r:TO_PATIENT]-(m)
    WHERE n.name = |patient_id| AND labels(n) = ["NeoPatient"] AND NOT labels(m) = ["NeoProtocol"] AND properties(r).attention IN [{DataImportanceFeature.NONE_IMPORTANCE.value}, {DataImportanceFeature.TRUE_IMPORTANCE.value}]
    RETURN labels(m)[0] AS class_parent_node, m.name AS name_parent_node, properties(r).value AS value_parent_node, properties(r).chain AS chain_parent_node, properties(r).attention AS attention, properties(r).score AS score, properties(r).protocol_pk AS protocol
    """
    CHANGE_ATTENTION_SCORE_RELATION = """MATCH (n:{class_feature})-[r]->(m)
    WHERE n.name = {name_feature} AND r.patient_id = {patient_id} AND r.protocol_pk = {protocol_pk} AND r.chain = {feature_chain} AND r.value = {feature_value}
    SET r.attention = {new_attention}, r.score = {new_score}
    """
    CHANGE_ATTENTION_RELATION = """MATCH (n:{class_feature})-[r]->(m)
    WHERE n.name = {name_feature} AND r.patient_id = {patient_id} AND r.protocol_pk = {protocol_pk} AND r.chain = {feature_chain} AND r.value = {feature_value}
    SET r.attention = {new_attention}
    """
    UNIQUE_ATTENTION_IN_PROTOCOL = """MATCH (n)-[r:TO_PROTOCOL]-(m)
    WHERE n.name = {protocol_pk} AND n.patient_id = {patient_id} AND labels(n) = ["NeoProtocol"] AND NOT labels(m) = ["NeoPatient"]
    RETURN DISTINCT properties(r).attention AS attention
    """
    DISEASE_OF_PROTOCOL = """MATCH (n:NeoProtocol)-[r]-(m:NeoDisease)
    WHERE n.name IN {protocol_ids} AND r.patient_id={patient_id}
    RETURN DISTINCT m.name AS diases, n.name AS protocol
    """
    CONTAINS_CHAIN_ONE_PROTOCOL = """MATCH (n)-[r]-(m:NeoProtocol)
    WHERE r.protocol_pk = {protocol_pk} AND r.chain CONTAINS {chain} AND NOT n.name = {name_feature} AND r.value = {value}
    RETURN n.name AS name_parent_node, labels(n)[0] AS class_parent_node, properties(r).value AS value_parent_node, properties(r).chain AS chain
    """
    IS_CONNECTION_BETWEEN_NODES = """MATCH path=(n:{class_daughter} {name: {name_daughter}})-[r]->(m:{class_parent} {name: {name_parent}})
    WHERE r.protocol_pk = {protocol_pk} AND r.chain CONTAINS {chain} AND r.value = {value_daughter}
    RETURN path
    """
