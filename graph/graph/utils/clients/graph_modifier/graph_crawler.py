import logging
from typing import List, Optional, Union

from django.conf import settings
from neomodel import db

from akcent_graph.apps.medaggregator.cypher_templates import DataCypherQueriesNeoSpider
from akcent_graph.apps.medaggregator.helpers import (
    DataConnectAbility,
    DataCreatedByNeuro,
    DataParentNotFound,
    DataPromptAbility,
    DataRelationshipNamingByNeuro,
)
from akcent_graph.utils.clients.gpt.call_gpt import GPT
from akcent_graph.utils.clients.gpt.prompts import (
    get_prompt_of_diseases_entities_classifier,
    get_prompt_of_entities_classifier,
)
from akcent_graph.utils.clients.graph_modifier.entities_similary import EntityFinder
from akcent_graph.utils.neo.crud_operator import Neo4jCRUD

logger = logging.getLogger(__name__)


class NeoSpider:
    """
    Finding parent or child for entities without parents
    ====================================================

    Methods:
    --------
    \n\t__init__
    \n\tget_nodes_without_parents
    \n\tfind_parent_and_child_classes_for_class
    \n\tis_relationship
    \n\tcheck_and_change
    \n\tfind_doubles

    """

    def __init__(
        self,
        with_prompt_check: bool = DataPromptAbility.PROMPT_CHECK_TRUE.value,
        is_relationship: str = DataConnectAbility.SWITCH_ON.value,
        is_test: bool = False,
        excluded_classes: List[str] = ['NeoProtocol', 'NeoPatient'],
    ) -> None:
        """Init method for NeoSpider.\n
        with_prompt_check: special flag for prompt_check\n
        is_relationship: if '1' - skip method is_relationship\n
        is_test: special flag for testing
        """
        self.with_prompt_check = with_prompt_check
        self.relationship = is_relationship
        self.is_test = is_test
        self.excluded_classes = excluded_classes
        self.neo4jcrud = Neo4jCRUD()

    def get_nodes_without_parents(
        self,
        query: str = DataCypherQueriesNeoSpider.NODES_WITHOUT_PARENTS.value,
    ) -> tuple[tuple[List[str], dict[str, str], dict[str, Union[str, dict[str, str]]]]]:
        """Get all nodes from graphdb without  parents.\n
        This method return list with node labels, node properties and relationship type
        or only query_nodes for testing.\n
        query: query to graphdb to get nodes without parents
        """
        params = {
            'parent_value': DataParentNotFound.NOT_FOUND_PARENT.value,
        }
        if not self.is_test:
            find_nodes, _ = db.cypher_query(query, params)
            return find_nodes
        else:
            return (([query], {}, {}),)

    def find_parent_and_child_classes_for_class(
        self,
        node_class: str,
        manual_dictionary: bool = False,
        query: str = DataCypherQueriesNeoSpider.PARENT_AND_CHILD_CLASSES_FOR_CLASS.value,
    ) -> tuple[List[str]]:
        """Find parent and child classes for current class according graphdb.\n
        This method return list with current class label and lists of possible
        parent and child class labels
        or only query_possible_classes for testing.\n
        query: query to graphdb to get possible child and parent classes\n
        node_class: current class name\n
        manual_dictionary: special flag for manual input or another way to achieve of possible classes
        according to the architecture of graphdb
        is_test: special flag for testing
        """
        if manual_dictionary:
            return (['Here return manual dictionary instead of this string!'],)
        else:
            query_possible_classes = query.format(
                current_class_name=node_class,
            )
            if not self.is_test:
                find_possible_classes, _ = db.cypher_query(query_possible_classes)
                return find_possible_classes
            else:
                return ([query_possible_classes],)

    def is_relationship(
        self,
        possible_daughter_entity: str,
        possible_parent_entity: str,
    ) -> str:
        """Binary classification using prompt.\n
        This method compares two entities, whether one of them is a part of the other.\n
        possible_daughter_entity: name of daughter entity\n
        possible_parent_entity: name of parent entity\n
        answer_of_gpt: is '0' if no comparison and is '1' otherwise
        """
        gpt = GPT()
        system_role, user_role = get_prompt_of_entities_classifier(
            daughter_entity=possible_daughter_entity,
            parent_entity=possible_parent_entity,
        )
        answer_of_gpt = str(gpt.make_request(system_prompt=system_role, prompt=user_role))
        return answer_of_gpt

    def check_and_change(  # noqa: C901, pylint: disable=too-complex
        self,
    ) -> None:
        """This method find parents (childs) for entity without parents
        and merge relationships to graphdb changing value of property key parent_not_found.
        """
        entityfinder = EntityFinder()
        nodes_without_parents = self.get_nodes_without_parents()
        for node_without_parent in nodes_without_parents:
            node_class_without_relationships = node_without_parent[0][0]
            node_name_without_relationships = node_without_parent[1].get('name')
            relation = node_without_parent[2]
            relation_properties = relation._properties  # type: ignore
            patient_id = relation_properties.get('patient_id')
            protocol_pk = relation_properties.get('protocol_pk')
            possible_classes = self.find_parent_and_child_classes_for_class(
                node_class=node_class_without_relationships,
            )
            lower_classes = [item for item in possible_classes[0][1] if item not in set(self.excluded_classes)]
            if lower_classes and node_name_without_relationships:
                for possible_lower_class in lower_classes:
                    possible_child_names = entityfinder.get_similary_entity(
                        entity_name=str(node_name_without_relationships),
                        name_targetclass=possible_lower_class,
                    )
                    if self.with_prompt_check:
                        for possible_child_name in possible_child_names:
                            relationship = self.is_relationship(
                                possible_daughter_entity=possible_child_name,
                                possible_parent_entity=str(node_name_without_relationships),
                            )
                            if relationship == self.relationship:
                                break
                    else:
                        relationship = self.relationship
                    if relationship == self.relationship:
                        spider_chain = (
                            possible_child_names[0] + settings.CHAIN_SEPARATOR + str(node_name_without_relationships)
                        )
                        self.neo4jcrud.merge_nodes_and_relationships_by_neuro(
                            start_node_label=node_class_without_relationships,
                            start_node_name=str(node_name_without_relationships),
                            end_node_label=possible_lower_class,
                            end_node_name=possible_child_names[0],
                            chain=spider_chain,
                            protocol_pk=-1,
                            patient_id=-1,
                            relationship_type=DataRelationshipNamingByNeuro.SPIDER_1_NAME.value,
                            created_by_neuro=DataCreatedByNeuro.SPIDER_1.value,
                        )
                        spider_chain_back = (
                            str(node_name_without_relationships) + settings.CHAIN_SEPARATOR + possible_child_names[0]
                        )
                        self.neo4jcrud.merge_nodes_and_relationships_by_neuro(
                            start_node_label=possible_lower_class,
                            start_node_name=possible_child_names[0],
                            end_node_label=node_class_without_relationships,
                            end_node_name=str(node_name_without_relationships),
                            chain=spider_chain_back,
                            protocol_pk=protocol_pk,
                            patient_id=patient_id,
                            relationship_type=DataRelationshipNamingByNeuro.SPIDER_1_NAME.value,
                            created_by_neuro=DataCreatedByNeuro.SPIDER_1.value,
                        )
                        self.neo4jcrud.merge_nodes_and_relationships_by_neuro(
                            start_node_label=possible_lower_class,
                            start_node_name=possible_child_names[0],
                            end_node_label='NeoProtocol',
                            end_node_name=protocol_pk,
                            chain=spider_chain_back,
                            protocol_pk=protocol_pk,
                            patient_id=patient_id,
                            relationship_type=DataRelationshipNamingByNeuro.SPIDER_1_NAME.value,
                            created_by_neuro=DataCreatedByNeuro.SPIDER_1.value,
                        )
                        self.neo4jcrud.merge_nodes_and_relationships_by_neuro(
                            start_node_label=possible_lower_class,
                            start_node_name=possible_child_names[0],
                            end_node_label='NeoPatient',
                            end_node_name=patient_id,
                            chain=spider_chain_back,
                            protocol_pk=patient_id,
                            patient_id=patient_id,
                            relationship_type=DataRelationshipNamingByNeuro.SPIDER_1_NAME.value,
                            created_by_neuro=DataCreatedByNeuro.SPIDER_1.value,
                        )
                        self.neo4jcrud.match_parent_not_found_key_value_by_neuro(
                            start_node_label='NeoProtocol',
                            start_node_name=protocol_pk,
                            end_node_label=node_class_without_relationships,
                            end_node_name=str(node_name_without_relationships),
                            chain=spider_chain_back,
                            protocol_pk=protocol_pk,
                            patient_id=patient_id,
                            relationship_type=DataRelationshipNamingByNeuro.SPIDER_1_NAME.value,
                            created_by_neuro=DataCreatedByNeuro.TRUE.value,
                            parent_not_found=DataParentNotFound.FOUND_PARENT.value,
                        )
                        self.neo4jcrud.match_parent_not_found_key_value_by_neuro(
                            start_node_label='NeoPatient',
                            start_node_name=patient_id,
                            end_node_label=node_class_without_relationships,
                            end_node_name=str(node_name_without_relationships),
                            chain=spider_chain_back,
                            protocol_pk=protocol_pk,
                            patient_id=patient_id,
                            relationship_type=DataRelationshipNamingByNeuro.SPIDER_1_NAME.value,
                            created_by_neuro=DataCreatedByNeuro.TRUE.value,
                            parent_not_found=DataParentNotFound.FOUND_PARENT.value,
                        )
            upper_classes = [item for item in possible_classes[0][2] if item not in set(self.excluded_classes)]
            if upper_classes and node_name_without_relationships:
                for possible_upper_class in upper_classes:
                    possible_parent_names = entityfinder.get_similary_entity(
                        entity_name=str(node_name_without_relationships),
                        name_targetclass=possible_upper_class,
                    )
                    if self.with_prompt_check:
                        for possible_parent_name in possible_parent_names:
                            relationship = self.is_relationship(
                                possible_daughter_entity=str(node_name_without_relationships),
                                possible_parent_entity=possible_parent_name,
                            )
                            if relationship == self.relationship:
                                break
                    else:
                        relationship = self.relationship
                    if relationship == self.relationship:
                        spider_chain = (
                            str(node_name_without_relationships) + settings.CHAIN_SEPARATOR + possible_parent_names[0]
                        )
                        self.neo4jcrud.merge_nodes_and_relationships_by_neuro(
                            start_node_label=possible_upper_class,
                            start_node_name=possible_parent_names[0],
                            end_node_label=node_class_without_relationships,
                            end_node_name=str(node_name_without_relationships),
                            chain=spider_chain,
                            protocol_pk=-1,
                            patient_id=-1,
                            relationship_type=DataRelationshipNamingByNeuro.SPIDER_1_NAME.value,
                            created_by_neuro=DataCreatedByNeuro.SPIDER_1.value,
                        )
                        spider_chain_back = (
                            possible_parent_names[0] + settings.CHAIN_SEPARATOR + str(node_name_without_relationships)
                        )
                        self.neo4jcrud.merge_nodes_and_relationships_by_neuro(
                            start_node_label=node_class_without_relationships,
                            start_node_name=str(node_name_without_relationships),
                            end_node_label=possible_upper_class,
                            end_node_name=possible_parent_names[0],
                            chain=spider_chain_back,
                            protocol_pk=protocol_pk,
                            patient_id=patient_id,
                            relationship_type=DataRelationshipNamingByNeuro.SPIDER_1_NAME.value,
                            created_by_neuro=DataCreatedByNeuro.SPIDER_1.value,
                        )
                        self.neo4jcrud.merge_nodes_and_relationships_by_neuro(
                            start_node_label=possible_upper_class,
                            start_node_name=possible_parent_names[0],
                            end_node_label='NeoProtocol',
                            end_node_name=protocol_pk,
                            chain=spider_chain_back,
                            protocol_pk=protocol_pk,
                            patient_id=patient_id,
                            relationship_type=DataRelationshipNamingByNeuro.SPIDER_1_NAME.value,
                            created_by_neuro=DataCreatedByNeuro.SPIDER_1.value,
                        )
                        self.neo4jcrud.merge_nodes_and_relationships_by_neuro(
                            start_node_label=possible_upper_class,
                            start_node_name=possible_parent_names[0],
                            end_node_label='NeoPatient',
                            end_node_name=patient_id,
                            chain=spider_chain_back,
                            protocol_pk=protocol_pk,
                            patient_id=patient_id,
                            relationship_type=DataRelationshipNamingByNeuro.SPIDER_1_NAME.value,
                            created_by_neuro=DataCreatedByNeuro.SPIDER_1.value,
                        )
                        self.neo4jcrud.match_parent_not_found_key_value_by_neuro(
                            start_node_label='NeoProtocol',
                            start_node_name=protocol_pk,
                            end_node_label=node_class_without_relationships,
                            end_node_name=str(node_name_without_relationships),
                            chain=spider_chain_back,
                            protocol_pk=protocol_pk,
                            patient_id=patient_id,
                            relationship_type=DataRelationshipNamingByNeuro.SPIDER_1_NAME.value,
                            created_by_neuro=DataCreatedByNeuro.TRUE.value,
                            parent_not_found=DataParentNotFound.FOUND_PARENT.value,
                        )
                        self.neo4jcrud.match_parent_not_found_key_value_by_neuro(
                            start_node_label='NeoPatient',
                            start_node_name=patient_id,
                            end_node_label=node_class_without_relationships,
                            end_node_name=str(node_name_without_relationships),
                            chain=spider_chain_back,
                            protocol_pk=protocol_pk,
                            patient_id=patient_id,
                            relationship_type=DataRelationshipNamingByNeuro.SPIDER_1_NAME.value,
                            created_by_neuro=DataCreatedByNeuro.TRUE.value,
                            parent_not_found=DataParentNotFound.FOUND_PARENT.value,
                        )

    def find_doubles(
        self,
        node_class: str,
        query: str = DataCypherQueriesNeoSpider.FIND_DOUBLES.value,
    ) -> List[List[Optional[str | int | List[int]]]]:
        query_doubles_entities = query.format(
            current_class_name=node_class,
        )
        if not self.is_test:
            find_doubles_entities, _ = db.cypher_query(query_doubles_entities)
            return find_doubles_entities
        else:
            return [[query_doubles_entities]]

    def delete_brief_doubles(
        self,
        classes: list[str] = ['NeoProtocol', 'NeoPatient'],
    ) -> None:
        for current_class in classes:
            found_doubles = self.find_doubles(current_class)
            doubles_ids = found_doubles[0][1]
            count_max: int = -1
            pop_index: int = -1
            if isinstance(doubles_ids, list):
                for index, doubles_id in enumerate(doubles_ids):
                    pop_index = pop_index
                    count_doubles_id = self.neo4jcrud.count_relations_by_id(doubles_id)[0][0][1]
                    if count_doubles_id > count_max:
                        count_max = count_doubles_id
                        pop_index = index
                doubles_ids.pop(pop_index)
                doubles_delete_ids = doubles_ids
                for delete_id in doubles_delete_ids:
                    self.neo4jcrud.detach_delete_entity_by_id(
                        entity_id=str(delete_id),
                    )


class NeoSpiderDiseaseMatcher:
    """
    Match not matched diseases with disease MKB-10 if it is possible
    ================================================================

    Methods:
    --------
    \n\t__init__
    \n\tfind_not_matched_diseases
    \n\tis_disease_matching_ability
    \n\tneodisease_nodes_checker

    """

    def __init__(
        self,
        with_prompt_check: bool = DataPromptAbility.PROMPT_CHECK_TRUE.value,
        is_disease_matching_ability: str = DataConnectAbility.SWITCH_ON.value,
        is_test: bool = False,
    ) -> None:
        """Init method for NeoSpiderDiseaseMatcher.\n
        with_prompt_check: special flag for prompt_check\n
        is_disease_matching_ability: if '1' - do match\n
        is_test: special flag for testing
        """
        self.with_prompt_check = with_prompt_check
        self.disease_matching_ability = is_disease_matching_ability
        self.is_test = is_test
        self.neo4jcrud = Neo4jCRUD()

    def find_not_matched_diseases(
        self,
        query: str = DataCypherQueriesNeoSpider.NOT_MATCHED_DISEASES.value,
    ) -> List[List[Union[str, int]]]:
        if not self.is_test:
            diseases_names_with_id, _ = db.cypher_query(query)
            return diseases_names_with_id
        else:
            return [[query]]

    def is_disease_matching_ability(
        self,
        disease_name: str,
        disease_entity: str,
    ) -> str:
        """Binary classification using prompt.\n
        This method compares two entities, whether one of them is a part of the other.\n
        disease_name: name of current disease to match\n
        disease_entity: name of disease entity (MKB-10)\n
        answer_of_gpt: is '0' if no comparison and is '1' otherwise
        """
        gpt = GPT()
        system_role, user_role = get_prompt_of_diseases_entities_classifier(
            disease_name=disease_name,
            disease_entity=disease_entity,
        )
        answer_of_gpt = str(gpt.make_request(system_prompt=system_role, prompt=user_role))
        return answer_of_gpt

    def transfer_all_relationships(
        self,
        source_id: str,
        target_id: str,
        query: str = DataCypherQueriesNeoSpider.TRANSFER_ALL_RELATIONSHIPS.value,
    ) -> tuple[tuple[List[str], dict[str, str], dict[str, Union[str, dict[str, str]]]]]:
        """Transfer relationships by cypher only.\n
        This method transfer all relationships.\n
        source_id: id of current disease to match\n
        target_id: id of disease entity (MKB-10)\n
        """
        query_all_relationships = query.format(
            source_id=source_id,
            target_id=target_id,
        )
        if not self.is_test:
            db.cypher_query(query_all_relationships)
            return (([query_all_relationships], {}, {}),)
        else:
            return (([query_all_relationships], {}, {}),)

    def find_all_relationships(
        self,
        source_id: Union[str, int],
        query: str = DataCypherQueriesNeoSpider.FIND_ALL_RELATIONSHIPS.value,
    ) -> tuple[tuple[List[str], dict[str, str], dict[str, Union[str, dict[str, str]]]]]:
        """Find all outcoming and incoming relationships by id.\n
        This method compares two entities, whether one of them is a part of the other.\n
        source_id: id of current disease to match\n
        """
        query_all_relationships = query.format(
            source_id=source_id,
        )
        if not self.is_test:
            relationships, _ = db.cypher_query(query_all_relationships)
            return relationships
        else:
            return (([query_all_relationships], {}, {}),)

    def neodisease_nodes_checker(  # noqa: C901, pylint: disable=too-complex
        self,
        data_path: str = settings.ENTITIES_NEODISEASE_DATA_PATH,
        name_target_class: str = 'NeoDisease',
        number_of_diseases: int = 5,
        is_matched: bool = False,
        is_relocated: bool = False,
    ) -> None:
        is_matched = is_matched
        is_relocated = is_relocated
        entityfinder_neodisease = EntityFinder(data_path=data_path)
        diseases_names_with_id = self.find_not_matched_diseases()
        if diseases_names_with_id:
            for disease_name_with_id in diseases_names_with_id:
                current_disease_name = disease_name_with_id[0]
                current_disease_id = disease_name_with_id[1]
                source_id = str(current_disease_id)
                if len(self.find_all_relationships(source_id)) == 0:
                    self.neo4jcrud.detach_delete_entity_by_id(source_id)
                    continue
                diseases_entities = entityfinder_neodisease.get_similary_entity(
                    entity_name=str(current_disease_name),
                    name_targetclass=name_target_class,
                )[0:number_of_diseases]
                for disease_entity in diseases_entities:
                    is_matched = False
                    if current_disease_name and disease_entity:
                        matching_ability = self.is_disease_matching_ability(
                            disease_name=str(current_disease_name),
                            disease_entity=disease_entity,
                        )
                    else:
                        matching_ability = DataConnectAbility.SWITCH_OFF.value
                        continue
                    if matching_ability == self.disease_matching_ability:
                        relations = self.find_all_relationships(source_id=source_id)
                        target_id = '-1'
                        target_id_response = []
                        target_id_response = self.neo4jcrud.return_id_by_name_and_class_name(
                            entity_name=disease_entity,
                            entity_class='NeoDisease',
                        )
                        if target_id_response:
                            try:
                                target_id = str(target_id_response[0][0])
                            except IndexError as error:
                                logger.info(
                                    'disease_entity: %s.\nTry to find disease_entity in graphdb, that exists in entities_neodisease.pkl!\n',
                                    disease_entity,
                                )
                                logger.error(error)
                        if isinstance(target_id, str) and target_id != '-1':
                            self.transfer_all_rels(
                                relations=relations,
                                source_id=source_id,
                                target_id=target_id,
                            )
                            is_matched = True
                            break
                    else:
                        is_matched = False
                        continue
                if not is_matched:
                    self.neo4jcrud.rename_label(
                        current_id=source_id,
                        old_label='NeoDisease',
                        new_label='NeoProtocolValue',
                    )
                    is_relocated = True

    def transfer_all_rels(
        self,
        relations: tuple[tuple[List[str], dict[str, str], dict[str, Union[str, dict[str, str]]]]],
        source_id: Union[str, int],
        target_id: Union[str, int],
        detach_delete_source: bool = True,
    ) -> None:
        for relation in relations:
            start_id = relation[0].nodes[0].element_id  # type: ignore
            if str(start_id) == str(source_id):
                start_id = target_id
            end_id = relation[0].nodes[1].element_id  # type: ignore
            if str(end_id) == str(source_id):
                end_id = target_id
            relationship_type = relation[0].type  # type: ignore
            relationship_properties = relation[0]._properties  # type: ignore
            relation_info = (start_id, end_id, relationship_type, relationship_properties)
            self.neo4jcrud.create_relation_by_info(relation_info)
        if detach_delete_source:
            self.neo4jcrud.detach_delete_entity_by_id(str(source_id))
