# pylint: disable=duplicate-code
"""
Module for testing of cypher queries.
==========================================

Classes:
----------
TestNeo4jCRUD:
    \n\ttest_merge_nodes_and_relationships_by_neuro
    \n\ttest_match_parent_not_found_key_value_by_neuro
    \n\ttest_delete_entity
    \n\ttest_detach_delete_entity
    \n\ttest_detach_delete_entity_by_id
    \n\ttest_count_relations_by_id

TestNeoSpider:
    \n\ttest_get_nodes_without_parents
    \n\ttest_find_parent_and_child_classes_for_class
    \n\ttest_find_doubles
    \n\ttest_neodisease_nodes_checker

Dependencies:
-------------
django

"""


from django.test.testcases import TestCase

from akcent_graph.apps.medaggregator.helpers import DataCreatedByNeuro, DataImportanceFeature, DataParentNotFound
from akcent_graph.utils.clients.cypher_validator.cypher_validator import validate_query
from akcent_graph.utils.clients.graph_modifier.graph_crawler import NeoSpider, NeoSpiderDiseaseMatcher
from akcent_graph.utils.neo.crud_operator import Neo4jCRUD


class TestNeo4jCRUD(TestCase):
    """
    Tests for akcent_graph.utils.neo.crud_operator.py
    ================================================

    Methods:
    --------
    \n\ttest_merge_nodes_and_relationships_by_neuro
    \n\ttest_match_parent_not_found_key_value_by_neuro
    \n\ttest_delete_entity
    \n\ttest_detach_delete_entity

    """

    def setUp(self) -> None:
        self.neo4jcrud = Neo4jCRUD(is_test=True)

    def test_merge_nodes_and_relationships_by_neuro(self) -> None:
        start_node_label = 'NeoOrgan'
        start_node_name = 'сердце'
        end_node_label = 'NeoOrganStructure'
        end_node_name = 'митральный клапан'
        chain = 'сердце$iamb$митральный клапан'
        value = ['стабильное сердцебиение']
        protocol_pk = 15
        patient_id = 5
        relationship_type = 'CREATED_BY_NEURO'
        created_by_neuro = DataCreatedByNeuro.TRUE.value
        attention = DataImportanceFeature.NONE_IMPORTANCE.value
        answer = """\
        MERGE (child:`NeoOrgan` {name: $name_child})
        MERGE (parent:`NeoOrganStructure` {name: $name_parent})
        MERGE (child)-[:`CREATED_BY_NEURO` {
            chain: $chain,
            value: $value,
            protocol_pk: $protocol_pk,
            patient_id: $patient_id,
            created_by_neuro: $created_by_neuro,
            attention: $attention}]->(parent)
        """
        query = self.neo4jcrud.merge_nodes_and_relationships_by_neuro(
            start_node_label=start_node_label,
            start_node_name=start_node_name,
            end_node_label=end_node_label,
            end_node_name=end_node_name,
            chain=chain,
            value=value,
            protocol_pk=protocol_pk,
            patient_id=patient_id,
            relationship_type=relationship_type,
            created_by_neuro=created_by_neuro,
            attention=attention,
        )
        self.assertEqual(
            query,
            answer,
        )
        self.assertEqual(
            validate_query(query),
            True,
        )

    def test_match_parent_not_found_key_value_by_neuro(self) -> None:
        start_node_label = 'NeoOrgan'
        start_node_name = 'сердце'
        end_node_label = 'NeoProtocol'
        end_node_name = 5
        chain = 'сердце'
        protocol_pk = 15
        patient_id = 5
        relationship_type = 'CREATED_BY_NEURO'
        created_by_neuro = DataCreatedByNeuro.TRUE.value
        parent_not_found = DataParentNotFound.FOUND_PARENT.value

        answer = """\
        MATCH (start:`NeoOrgan` {name: $name_start})<-[r]-(end:`NeoProtocol` {name: $name_end})
        WHERE r.patient_id=5 and r.protocol_pk=15
        SET r.parent_not_found=0
        SET r.chain='сердце'
        SET r.created_by_neuro=2
        """

        query = self.neo4jcrud.match_parent_not_found_key_value_by_neuro(
            start_node_label=start_node_label,
            start_node_name=start_node_name,
            end_node_label=end_node_label,
            end_node_name=end_node_name,
            chain=chain,
            protocol_pk=protocol_pk,
            patient_id=patient_id,
            relationship_type=relationship_type,
            created_by_neuro=created_by_neuro,
            parent_not_found=parent_not_found,
        )
        self.assertEqual(
            query,
            answer,
        )
        self.assertEqual(
            validate_query(query),
            False,
        )

    def test_delete_entity(self) -> None:
        entity_name = 10
        entity_class = 'NeoPatient'
        answer = """\
        MATCH (n:`NeoPatient` {name: $name})
        WHERE NOT (n)--()
        DELETE n;
        """
        query = self.neo4jcrud.delete_entity(
            entity_name=entity_name,
            entity_class=entity_class,
        )
        self.assertEqual(
            query,
            answer,
        )
        self.assertEqual(
            validate_query(query),
            True,
        )

    def test_detach_delete_entity(self) -> None:
        entity_name = 10
        entity_class = 'NeoProtocol'
        answer = """\
        MATCH (n:`NeoProtocol` {name: $name})
        DETACH DELETE n;
        """
        query = self.neo4jcrud.detach_delete_entity(
            entity_name=entity_name,
            entity_class=entity_class,
        )
        self.assertEqual(
            query,
            answer,
        )
        self.assertEqual(
            validate_query(query),
            True,
        )

    def test_detach_delete_entity_by_id(self) -> None:
        entity_id = 34265
        answer = """\
        MATCH (entity)
        WHERE ID(entity) = 34265
        DETACH DELETE entity;
        """
        query = self.neo4jcrud.detach_delete_entity_by_id(
            entity_id=str(entity_id),
        )
        self.assertEqual(
            query,
            answer,
        )
        self.assertEqual(
            validate_query(query),
            True,
        )

    def test_count_relations_by_id(self) -> None:
        entity_id = 23187
        answer: str = """\
        MATCH (entity)
        WHERE ID(entity) = 23187
        OPTIONAL MATCH ()-[relationship_in]->(entity)
        WITH entity, count(relationship_in) AS incoming_relationships
        OPTIONAL MATCH (entity)-[relationship_out]->()
        RETURN ID(entity) AS entity_id, incoming_relationships + count(relationship_out) AS total_connections, incoming_relationships, count(relationship_out) AS outcoming_relationships;
        """
        query = self.neo4jcrud.count_relations_by_id(
            entity_id=entity_id,
        )
        self.assertEqual(
            query,
            answer,
        )
        self.assertEqual(
            validate_query(query),
            True,
        )


class TestNeoSpider(TestCase):
    """
    Tests for akcent_graph.utils.clients.graph_modifier.graph_crawler.py
    ====================================================================

    Methods:
    --------
    \n\ttest_get_nodes_without_parents
    \n\ttest_find_parent_and_child_classes_for_class
    \n\ttest_find_doubles
    \n\ttest_neodisease_nodes_checker

    """

    def setUp(self) -> None:
        self.neospider = NeoSpider(is_test=True)
        self.neospider_disease_matcher = NeoSpiderDiseaseMatcher(is_test=True)

    def test_get_nodes_without_parents(self) -> None:
        answer = """\
        MATCH (n)-[r]->(m) WHERE r.parent_not_found=$parent_value
        RETURN labels(n), properties(n), r
        """
        query = self.neospider.get_nodes_without_parents()[0][0][0]
        self.assertEqual(
            query,
            answer,
        )
        self.assertEqual(
            validate_query(query),
            True,
        )

    def test_find_parent_and_child_classes_for_class(self) -> None:
        node_class = 'NeoOrgan'
        answer = """\
        MATCH (current:`NeoOrgan`)
        OPTIONAL MATCH (current)-[downRel]->(lowerClass)
        WHERE downRel.patient_id = -1 and downRel.protocol_pk = -1
        OPTIONAL MATCH (upperClass)-[upRel]->(current)
        WHERE upRel.patient_id = -1 and upRel.protocol_pk = -1
        RETURN collect(DISTINCT labels(current)[0]) AS CurrentClass,
        collect(DISTINCT labels(lowerClass)[0]) AS LowerClasses,
        collect(DISTINCT labels(upperClass)[0]) AS UpperClasses;
        """

        query = self.neospider.find_parent_and_child_classes_for_class(
            node_class=node_class,
        )[
            0
        ][0]
        self.assertEqual(
            query,
            answer,
        )
        self.assertEqual(
            validate_query(query),
            True,
        )

    def test_find_doubles(self) -> None:
        node_class = 'NeoProtocol'
        answer = """\
        MATCH (n:`NeoProtocol`)
        WITH n.name AS name, COLLECT(n) AS nodes
        WHERE SIZE(nodes) > 1
        UNWIND nodes AS nodeInstance
        WITH name, ID(nodeInstance) AS id, SIZE(nodes) AS duplicate_count
        RETURN name, COLLECT(id) AS ids, duplicate_count
        ORDER BY duplicate_count DESC;
        """
        query = self.neospider.find_doubles(
            node_class=node_class,
        )[
            0
        ][0]
        self.assertEqual(
            query,
            answer,
        )
        self.assertEqual(
            validate_query(query),
            True,
        )

    def test_not_matched_diseases(self) -> None:
        answer = """\
        MATCH (n:NeoDisease)
        WHERE NOT EXISTS (n.level)
        RETURN n.name, id(n);
        """
        query = self.neospider_disease_matcher.find_not_matched_diseases()[0][0]
        self.assertEqual(
            query,
            answer,
        )
