import importlib
import logging
import uuid

# from collections import defaultdict
from typing import Any, List, Optional, Union

import numpy as np
from constance import config
from django.conf import settings
from neomodel import (
    CardinalityViolation,
    DoesNotExist,
    NeomodelException,
    RelationshipFrom,
    RelationshipManager,
    RelationshipTo,
    UniqueProperty,
    db,
)

from akcent_graph.apps.medaggregator.cypher_templates import DataCypherQueriesNeoSpider
from akcent_graph.apps.medaggregator.helpers import (
    DataCreatedByNeuro,
    DataImportanceFeature,
    DataParentNotFound,
    DataProtocolAttention,
    DataRelationshipNamingByNeuro,
)
from akcent_graph.apps.medaggregator.models import (
    NeoAnatomicalFeature,
    NeoAnatomicalValue,
    NeoAnomality,
    NeoBodyFluids,
    NeoBodyStructure,
    NeoDisease,
    NeoFeatureStructure,
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
    NeoOrganStructure,
    NeoPatient,
    NeoPatientAnthropometryFeature,
    NeoPatientAnthropometryValue,
    NeoPatientDemographyFeature,
    NeoPatientDemographyValue,
    NeoProtocol,
    NeoProtocolFeature,
    NeoSymptomFeature,
    NeoSymptomValue,
    NeoTherapyFeature,
    NeoTherapyValue,
)

# from akcent_graph.apps.medaggregator.query_db import QueryAnamnesis
from akcent_graph.utils.clients.gpt.call_gpt import GPT
from akcent_graph.utils.clients.gpt.prompts import get_prompt_of_description_extract
from akcent_graph.utils.clients.processing_of_anamnesis import ProcessingAnamnesis
from akcent_graph.utils.neo.date_checker import normalize_and_check_date
from akcent_graph.utils.neo.disease_mkb10_checker import is_valid_mkb_code
from akcent_graph.utils.neo.pathnames import find_paths_with_names
from akcent_graph.utils.neo.protocol_checker import parents_index_checker
from akcent_graph.utils.neo.regexp_cypher import convert_dict_to_special_string

# from pandas import DataFrame


logger = logging.getLogger(__name__)


class Neo4jCRUD:
    def __init__(
        self,
        is_test: bool = False,
    ) -> None:
        self.is_test = is_test

    def find_or_create_node(
        self,
        module_name: Any,
        class_name: Any,
        node_name: Any,
        patient_pk: Any,
        protocol_pk: Any,
        protocol_data: Any,
        attention_required: Any = DataImportanceFeature.NONE_IMPORTANCE.value,
    ) -> Any:
        # Dynamic module import
        module = importlib.import_module(module_name)

        # Getting a model class by name
        model_class = getattr(module, class_name)

        # Checking the existence of a node
        if model_class == NeoProtocol:
            nodes = model_class.nodes.filter(name=node_name).filter(
                patient_id=patient_pk,
            )
        elif model_class == NeoDisease:
            nodes = model_class.nodes.filter(treecode=node_name)
            if len(nodes) == 0:
                nodes = model_class.nodes.filter(name=node_name)
        else:
            nodes = model_class.nodes.filter(name=node_name)
        if len(nodes) == 0:
            # Creating a new node
            if model_class == NeoProtocol:
                new_node = model_class(
                    name=node_name,
                    patient_id=patient_pk,
                    # protocol_info=protocol_data,
                    attention_required=attention_required,
                ).save()
                return new_node, model_class
            elif model_class == NeoDisease:
                new_node = model_class(
                    name=node_name,
                    attention_required=attention_required,
                ).save()
                return new_node, model_class
            elif model_class in [NeoAnomality, NeoAnatomicalFeature, NeoAnatomicalValue]:
                new_node = model_class(
                    name=node_name,
                    attention_required=attention_required,
                ).save()
                return new_node, model_class
            else:
                new_node = model_class(name=node_name).save()
                return new_node, model_class
        else:
            # Returning an existing node
            if 'patients_ids' in dir(nodes[0]):
                patient_ids = nodes[0].patients_ids
                if not patient_ids:
                    nodes[0].patients_ids = [patient_pk]
                    nodes[0].save()
                elif patient_pk not in patient_ids:
                    logger.info(nodes[0].patients_ids)
                    nodes[0].patients_ids.append(patient_pk)
                    nodes[0].save()
                logger.info(nodes[0])
            return nodes[0], model_class

    def connect_nodes(
        self,
        start_node: Any,
        end_node: Any,
        patient_id: Any = -1,
        protocol_pk: Any = -1,
        prefix: str = 'to_',
        chain: str = '',
        value: Any = None,
        attention: Any = DataImportanceFeature.NONE_IMPORTANCE.value,
        current_time: Any = None,
        parent_not_found: Any = DataParentNotFound.FOUND_PARENT.value,
    ) -> Any:
        relationship_neuro = ('TO_' + end_node.__class__.__label__[3:]).upper()
        # Get all the attributes of the start_node
        attrs = dir(start_node)
        # Find an attribute starting with a given prefix
        connected = False
        for attr in attrs:
            if attr.startswith(prefix) and attr.endswith(end_node.__class__.__label__[3:].lower()):
                connected = True
                relation_attr = getattr(start_node, attr)
                # Check the relationship type
                if isinstance(relation_attr, RelationshipTo):
                    relation_attr.connect(
                        end_node,
                        {
                            'attention': attention,
                            'patient_id': patient_id,
                            'value': value,
                            'protocol_pk': protocol_pk,
                            'patient_id': patient_id,
                            'timestamp': current_time,
                            'parent_not_found': parent_not_found,
                        },
                    )
                elif isinstance(relation_attr, RelationshipFrom):
                    relation_attr.connect_from(end_node)
                elif isinstance(relation_attr, RelationshipManager):
                    # if True:  # (len(relation_attr.all_relationships(end_node))) < 1:
                    try:
                        relation_attr.connect(
                            end_node,
                            {
                                'attention': attention,
                                'chain': chain,
                                'value': value,
                                'protocol_pk': protocol_pk,
                                'patient_id': patient_id,
                                'timestamp': current_time,
                                'parent_not_found': parent_not_found,
                            },
                        )
                    except ValueError as error:
                        logger.info(
                            'Impossible to connect node %s with node %s by %s relation with neomodel. \n Warning: %s',
                            start_node.__class__.__label__,
                            end_node.__class__.__label__,
                            attr,
                            error,
                        )
                else:
                    raise TypeError(f'Wrong type of relation: {type(relation_attr)}')
        if (not connected) and (prefix == 'backto_'):
            if not isinstance(value, str):
                value = str(value)
            self.merge_nodes_and_relationships_by_neuro(
                start_node_label=str(start_node.__class__.__label__),
                start_node_name=start_node.name,
                end_node_label=str(end_node.__class__.__label__),
                end_node_name=end_node.name,
                chain=chain,
                value=value,
                protocol_pk=protocol_pk,
                patient_id=patient_id,
                relationship_type=relationship_neuro,
            )

    def create_nodes_and_relationships(  # noqa: C901, pylint: disable=too-complex
        self,
        patient_pk: Any,
        protocol_pk: Any,
        data_protocol: Any,
    ) -> None:
        data_protocol = parents_index_checker(data_protocol)
        current_time = ''
        protocol_date = ''
        for element in data_protocol:
            name_class = element.get('class')
            name = element.get('name')
            value = element.get('value')
            if name_class == 'NeoProtocolFeature' and name and name.lower() == 'дата' and value:
                protocol_date = value[0]
                break
        treecode_diseases = []  # type: ignore
        if (patient_pk != -1) and (protocol_pk != -1):
            patient_node = self.find_or_create_node(
                module_name='akcent_graph.apps.medaggregator.models',
                class_name='NeoPatient',
                node_name=patient_pk,
                patient_pk=patient_pk,
                protocol_pk=protocol_pk,
                protocol_data=data_protocol,
                attention_required=DataProtocolAttention.NONE_FIRST.value,
            )
            protocol_node = self.find_or_create_node(
                module_name='akcent_graph.apps.medaggregator.models',
                class_name='NeoProtocol',
                node_name=protocol_pk,
                patient_pk=patient_pk,
                protocol_pk=protocol_pk,
                protocol_data=data_protocol,
                attention_required=DataProtocolAttention.NONE_FIRST.value,
            )
            self.connect_nodes(
                patient_node[0],
                protocol_node[0],
                patient_pk,
                protocol_pk,
                prefix='to_',
            )  # patient_pk, protocol_pk, needed?
            self.connect_nodes(
                protocol_node[0],
                patient_node[0],
                patient_pk,
                protocol_pk,
                prefix='backto_',
            )  # patient_pk, protocol_pk, # needed?
        # direct_keys = ['parents']
        #  reversed_keys = ['backto_organ', 'backto_patient', 'backto_protocol']
        # full_keys = direct_keys  # + reversed_keys
        position_index = {}
        diseases = {}
        for position, record in enumerate(data_protocol):
            # Create a dictionary of index positions
            position_index[record['index']] = position
            # if record['class'] == 'NeoOrgan':
            #     organ_node = self.find_or_create_node(
            #         module_name='akcent_graph.apps.medaggregator.models',
            #         class_name=record['class'],
            #         node_name=record['name'],
            #         patient_pk=patient_pk,
            #         protocol_pk=protocol_pk,
            #         protocol_data=data_protocol,
            #     )
            if record.get('class') == 'NeoDisease':
                if not protocol_date:
                    protocol_date = ''
                if (not treecode_diseases) and (is_valid_mkb_code(record.get('name'))):
                    treecode_diseases_dict = self.get_all_entities_by_class_names([('NeoDisease', 'treecode')])
                    treecode_diseases = treecode_diseases_dict.get('NeoDisease')
                if record.get('attention'):
                    attention_required = record.get('attention')
                else:
                    attention_required = DataImportanceFeature.NONE_IMPORTANCE.value
                disease_match = record['name']
                # disease_value = record.get('value')
                # if disease_value == []:
                #     disease_value = None
                if (is_valid_mkb_code(record.get('name'))) and (disease_match in treecode_diseases):
                    disease_node = self.find_or_create_node(
                        module_name='akcent_graph.apps.medaggregator.models',
                        class_name=record['class'],
                        node_name=disease_match,
                        patient_pk=patient_pk,
                        protocol_pk=protocol_pk,
                        protocol_data=data_protocol,
                        attention_required=attention_required,
                    )
                    diseases[position] = disease_node
                    disease_match = disease_node[0].name
                    data_protocol[position]['name'] = disease_match
                else:
                    disease_node = NeoDisease.get_or_create({'name': disease_match})
                    diseases[position] = disease_node
                # self.connect_nodes(
                #     disease_node[0],
                #     patient_node[0],
                #     patient_pk,
                #     protocol_pk,
                #     prefix='backto_',
                #     chain=disease_match,
                #     value=disease_value,
                #     current_time=protocol_date,
                # )
                # self.connect_nodes(
                #     disease_node[0],
                #     protocol_node[0],
                #     patient_pk,
                #     protocol_pk,
                #     prefix='backto_',
                #     chain=disease_match,
                #     value=disease_value,
                #     current_time=protocol_date,
                # )
            # if record['class'] == 'NeoAnomality':
            #     if record.get('attention'):
            #         attention_required = record.get('attention')
            #     else:
            #         attention_required = DataImportanceFeature.NONE_IMPORTANCE.value
            #     anomality_node = self.find_or_create_node(
            #         module_name='akcent_graph.apps.medaggregator.models',
            #         class_name=record['class'],
            #         node_name=record['name'],
            #         patient_pk=patient_pk,
            #         protocol_pk=protocol_pk,
            #         protocol_data=data_protocol,
            #         attention_required=attention_required,
            #     )
            #     self.connect_nodes(
            #         anomality_node[0],
            #         patient_node[0],
            #         patient_pk,
            #         protocol_pk,
            #         prefix='backto_',
            #         chain=record['name'],
            #         # attention=2 # надо конкретное значение
            #     )  # patient_pk, protocol_pk, needed?
            # if record['class'] == 'NeoAnatomicalFeature':
            #     if record.get('attention'):
            #         attention_required = record.get('attention')
            #     else:
            #         attention_required = DataImportanceFeature.NONE_IMPORTANCE.value
            #     self.find_or_create_node(  # anatomical_node
            #         module_name='akcent_graph.apps.medaggregator.models',
            #         class_name=record['class'],
            #         node_name=record['name'],
            #         patient_pk=patient_pk,
            #         protocol_pk=protocol_pk,
            #         protocol_data=data_protocol,
            #         attention_required=attention_required,
            #     )
            # self.connect_nodes(
            #     anatomical_node[0],
            #     patient_node[0],
            #     patient_pk,
            #     protocol_pk,
            #     prefix='backto_',
            #     chain=record['name']
            #     # attention=2 # надо конкретное значение
            # )  # patient_pk, protocol_pk, needed?
        # Создаем словарь для быстрого доступа к узлам по индексам
        protocol_index_map = {row_js['index']: row_js for row_js in data_protocol}
        for position, record in enumerate(data_protocol):
            # Find or create the current node (a child node or a node without a parent node)
            parents_list = record.get('parents')
            values_list = record.get('value')
            attention = record.get('attention_required')
            child_node = []
            if record.get('class') != 'NeoDisease':
                child_node = self.find_or_create_node(
                    module_name='akcent_graph.apps.medaggregator.models',
                    class_name=record['class'],
                    node_name=record['name'],
                    patient_pk=patient_pk,
                    protocol_pk=protocol_pk,
                    protocol_data=data_protocol,
                )
            else:
                child_node = diseases[position]
            if (patient_pk != -1) and (protocol_pk != -1):  # and record.get('class') != 'NeoDisease':
                if record.get('class') != 'NeoDisease':
                    self.connect_nodes(
                        patient_node[0],
                        child_node[0],
                        prefix='to_',
                    )  # patient_pk, protocol_pk, needed?
                    self.connect_nodes(
                        protocol_node[0],
                        child_node[0],
                        prefix='to_',
                    )  # patient_pk, protocol_pk, needed?
                try:
                    path_from_up_default = find_paths_with_names(protocol_index_map, record.get('index'))
                    formatted_paths_default = [
                        settings.CHAIN_SEPARATOR.join(f'{item[0]}' for item in reversed(path))
                        for path in path_from_up_default
                    ]
                except RecursionError as error:
                    formatted_paths_default = ['']
                    logger.error(
                        'Protocol pk: %s.\nTry to made chain.\nfor index %s.\n',
                        protocol_pk,
                        record.get('index'),
                    )
                    logger.error(error)
                parent_default = record.get('parents')
                value_default = record.get('value')
                if values_list:
                    try:
                        path_from_up_default = find_paths_with_names(protocol_index_map, record.get('index'))
                        formatted_paths = [
                            settings.CHAIN_SEPARATOR.join(f'{item[0]}' for item in reversed(path))
                            for path in path_from_up_default
                        ]
                    except RecursionError as error:
                        formatted_paths = ['']
                        logger.error(
                            'Protocol pk: %s.\nTry to made chain.\n',
                            protocol_pk,
                        )
                        logger.error(
                            'for index %s.\n',
                            record.get('index'),
                        )
                        logger.error(error)
                    if not parents_list and record.get('class') != 'NeoDisease':
                        chain_tree = record.get('name')
                        value = record.get('value')
                        self.connect_nodes(
                            child_node[0],
                            patient_node[0],
                            patient_pk,
                            protocol_pk,
                            prefix='backto_',
                            chain=chain_tree,
                            value=value,
                            attention=attention,
                            current_time=current_time,
                            parent_not_found=DataParentNotFound.NOT_FOUND_PARENT.value,
                        )
                        self.connect_nodes(
                            child_node[0],
                            protocol_node[0],
                            patient_pk,
                            protocol_pk,
                            prefix='backto_',
                            chain=chain_tree,
                            value=value,
                            attention=attention,
                            current_time=current_time,
                            parent_not_found=DataParentNotFound.NOT_FOUND_PARENT.value,
                        )
                    for index, (parent, value) in enumerate(zip(parents_list, values_list)):
                        # _current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
                        parent_node_name, parent_class_name = '', ''
                        try:
                            parent_node_name = data_protocol[position_index[parent]]['name']
                            parent_class_name = data_protocol[position_index[parent]]['class']
                        except KeyError as error:
                            relations_patient = child_node[0].backto_patient.relationship(patient_node[0])
                            if relations_patient:
                                relations_patient.parent_not_found = DataParentNotFound.NOT_FOUND_PARENT.value
                                relations_patient.save()
                            relations_protocol = child_node[0].backto_protocol.relationship(protocol_node[0])
                            if relations_protocol:
                                relations_protocol.parent_not_found = DataParentNotFound.NOT_FOUND_PARENT.value
                                relations_protocol.save()
                            logger.error(
                                'Protocol pk: %s.\nTry to find not existing parent node.\n',
                                protocol_pk,
                            )
                            logger.error(
                                'Parent index %s not found.\n',
                                parent,
                            )
                            logger.error(error)
                        if parent_node_name and parent_class_name:
                            if (
                                parent_node_name == 'NeoProtocolFeature'
                                and normalize_and_check_date(parent_class_name) != 0
                            ):
                                current_time = normalize_and_check_date(parent_class_name)
                            parent_node = self.find_or_create_node(
                                module_name='akcent_graph.apps.medaggregator.models',
                                class_name=parent_class_name,
                                node_name=parent_node_name,
                                patient_pk=patient_pk,
                                protocol_pk=protocol_pk,
                                protocol_data=data_protocol,
                            )
                            try:
                                chain_tree = ''
                                chain_tree = formatted_paths[index]
                                if not chain_tree:
                                    chain_tree = record.get('name')
                            except IndexError as error:
                                chain_tree = record.get('name')
                                logger.error(
                                    'Protocol pk: %s.\nTry to get chain_tree.\n',
                                    protocol_pk,
                                )
                                logger.error(error)
                            self.connect_nodes(
                                child_node[0],
                                parent_node[0],
                                patient_pk,
                                protocol_pk,
                                prefix='backto_',
                                chain=chain_tree,
                                value=value,
                                attention=attention,
                                current_time=current_time,
                            )
                            # _current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
                            self.connect_nodes(
                                child_node[0],
                                patient_node[0],
                                patient_pk,
                                protocol_pk,
                                prefix='backto_',
                                chain=chain_tree,
                                value=value,
                                attention=attention,
                                current_time=current_time,
                            )
                            self.connect_nodes(
                                child_node[0],
                                protocol_node[0],
                                patient_pk,
                                protocol_pk,
                                prefix='backto_',
                                chain=chain_tree,
                                value=value,
                                attention=attention,
                                current_time=current_time,
                            )
                            # if organ_node and (organ_node[0].name in chain_tree):
                            #     self.connect_nodes(
                            #         child_node[0],
                            #         organ_node[0],
                            #         patient_pk,
                            #         protocol_pk,
                            #         prefix='backto_',
                            #         chain=chain_tree,
                            #         value=value,
                            #         attention=attention,
                            #         current_time=current_time,
                            #     )
                else:
                    # _current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
                    parent = parent_default
                    if len(parent) == 1 and (not value_default):
                        parent_node_name, parent_class_name = '', ''
                        try:
                            parent_node_name = data_protocol[position_index[parent[0]]]['name']
                            parent_class_name = data_protocol[position_index[parent[0]]]['class']
                        except KeyError as error:
                            relations_patient = child_node[0].backto_patient.relationship(patient_node[0])
                            if relations_patient:
                                relations_patient.parent_not_found = DataParentNotFound.NOT_FOUND_PARENT.value
                                relations_patient.save()
                            relations_protocol = child_node[0].backto_protocol.relationship(protocol_node[0])
                            if relations_protocol:
                                relations_protocol.parent_not_found = DataParentNotFound.NOT_FOUND_PARENT.value
                                relations_protocol.save()
                            logger.error(
                                'Protocol pk: %s.\nTry to find not existing parent node.\n',
                                protocol_pk,
                            )
                            logger.error(
                                'Parent index %s not found.\n',
                                parent[0],
                            )
                            logger.error(error)
                        if parent_node_name and parent_class_name:
                            parent_node = self.find_or_create_node(
                                module_name='akcent_graph.apps.medaggregator.models',
                                class_name=parent_class_name,
                                node_name=parent_node_name,
                                patient_pk=patient_pk,
                                protocol_pk=protocol_pk,
                                protocol_data=data_protocol,
                            )
                            try:
                                chain_tree = ''
                                chain_tree = formatted_paths_default[0]
                                if not chain_tree:
                                    chain_tree = record.get('name')
                            except IndexError as error:
                                chain_tree = record.get('name')
                                logger.error(
                                    'Protocol pk: %s.\nTry to get chain_tree.\n',
                                    protocol_pk,
                                )
                                logger.error(error)
                            self.connect_nodes(
                                child_node[0],
                                parent_node[0],
                                patient_pk,
                                protocol_pk,
                                prefix='backto_',
                                chain=chain_tree,
                                value=value_default,
                                attention=attention,
                                current_time=current_time,
                            )
                    elif not parent and record.get('class') != 'NeoDisease':
                        chain_tree = record.get('name')
                        value = record.get('value')
                        self.connect_nodes(
                            child_node[0],
                            patient_node[0],
                            patient_pk,
                            protocol_pk,
                            prefix='backto_',
                            chain=chain_tree,
                            value=value,
                            attention=attention,
                            current_time=current_time,
                            parent_not_found=DataParentNotFound.NOT_FOUND_PARENT.value,
                        )
                        self.connect_nodes(
                            child_node[0],
                            protocol_node[0],
                            patient_pk,
                            protocol_pk,
                            prefix='backto_',
                            chain=chain_tree,
                            value=value,
                            attention=attention,
                            current_time=current_time,
                            parent_not_found=DataParentNotFound.NOT_FOUND_PARENT.value,
                        )
                    if True:  # record.get('class') != 'NeoDisease':
                        parent_not_found = DataParentNotFound.FOUND_PARENT.value
                        try:
                            chain_tree = ''
                            chain_tree = formatted_paths_default[0]
                            if (not chain_tree) or (chain_tree == record.get('name')):
                                chain_tree = record.get('name')
                                parent_not_found = DataParentNotFound.NOT_FOUND_PARENT.value
                        except IndexError as error:
                            chain_tree = record.get('name')
                            parent_not_found = DataParentNotFound.NOT_FOUND_PARENT.value
                            logger.error(
                                'Protocol pk: %s.\nTry to get chain_tree.\n',
                                protocol_pk,
                            )
                            logger.error(error)
                        self.connect_nodes(
                            child_node[0],
                            protocol_node[0],
                            patient_pk,
                            protocol_pk,
                            prefix='backto_',
                            chain=chain_tree,
                            value=value_default,
                            attention=attention,
                            current_time=current_time,
                            parent_not_found=parent_not_found,
                        )
                        self.connect_nodes(
                            child_node[0],
                            patient_node[0],
                            patient_pk,
                            protocol_pk,
                            prefix='backto_',
                            chain=chain_tree,
                            value=value_default,
                            attention=attention,
                            current_time=current_time,
                            parent_not_found=parent_not_found,
                        )
            # if organ_node:
            #     self.connect_nodes(
            #         child_node[0],
            #         organ_node[0],
            #         patient_pk,
            #         protocol_pk,
            #         prefix='backto_',)  # patient_pk, protocol_pk, needed?
            # for key in full_keys:
            #     if record.get(key):
            #         # If there is a parent node, find it and create a connection
            #         if child_node:
            #             relations_patient = child_node[0].backto_patient.relationship(patient_node[0])
            #             relations_protocol = child_node[0].backto_protocol.relationship(protocol_node[0])
            #         else:
            #             relations_patient = None
            #             relations_protocol = None
            #         try:
            #             parent_node_index = record.get(key)
            #             if parent_node_index:
            #                 for index in parent_node_index:
            #                     node_name, class_name = '', ''
            #                     try:
            #                         node_name = data_protocol[position_index[index]]['name']
            #                         class_name = data_protocol[position_index[index]]['class']
            #                     except KeyError as error:
            #                         if relations_patient:
            #                             relations_patient.parent_not_found = DataParentNotFound.NOT_FOUND_PARENT.value
            #                             relations_patient.save()
            #                         if relations_protocol:
            #                             relations_protocol.parent_not_found = DataParentNotFound.NOT_FOUND_PARENT.value
            #                             relations_protocol.save()
            #                         logger.error(
            #                             'Protocol pk: %s.\nTry to find not existing parent node.\n',
            #                             protocol_pk,
            #                         )
            #                         logger.error(
            #                             'Index %s not found.\n',
            #                             index,
            #                         )
            #                         logger.error(error)
            #                     if node_name and class_name:
            #                         parent_node = self.find_or_create_node(
            #                             module_name='akcent_graph.apps.medaggregator.models',
            #                             class_name=class_name,
            #                             node_name=node_name,
            #                             patient_pk=patient_pk,
            #                             protocol_pk=protocol_pk,
            #                             protocol_data=data_protocol,
            #                         )
            #                         # if key == 'parents':
            #                         if parent_node and child_node:
            #                             if key == 'parents':
            #                                 prefix = 'to_'
            #                                 self.connect_nodes(
            #                                     parent_node[0],
            #                                     child_node[0],
            #                                     prefix=prefix,
            #                                 )
            #                             else:
            #                                 prefix = key
            #                                 self.connect_nodes(
            #                                     parent_node[0],
            #                                     child_node[0],
            #                                     patient_pk,
            #                                     protocol_pk,
            #                                     prefix=prefix,
            #                                 )
            #                 # else:
            #                 #     self.connect_nodes(child_node[0], parent_node[0], prefix=prefix)
            #         except DoesNotExist as error:
            #             logger.error(
            #                 "Parent node with %s doesn't exist.",
            #                 record.get(key),
            #                 error,
            #             )

    def createpatientNode(
        self,
        name: Any,
    ) -> None:
        try:
            NeoPatient.get_or_create({'name': name})
        except UniqueProperty as e:
            raise e

    def createprotocolNode(
        self,
        name: Any,
        patient_id: Any,
        protocol_info: Any,
    ) -> None:
        try:
            timestamp = protocol_info.get('timestamp')
            attention_required = protocol_info.get('attention_required')
            NeoProtocol.get_or_create(
                {
                    'name': name,
                    'timestamp': str(timestamp),
                    'attention_required': attention_required,
                    'patient_id': patient_id,
                    # 'protocol_info': protocol_info,
                },
            )
        except UniqueProperty as e:
            raise e

    def createprotocolfeatureNode(
        self,
        name: Any,
        attention_required: Any,
    ) -> None:
        try:
            NeoProtocolFeature.get_or_create(
                {
                    'name': name,
                    'attention_required': attention_required,
                    'patients_ids': [],
                    'patients_json': {},
                },
            )
        except UniqueProperty as e:
            raise e

    def creatediseaseNode(
        self,
        name: Any,
        attention_required: bool = False,
    ) -> None:
        try:
            NeoDisease.get_or_create(
                {
                    'name': name,
                    'attention_required': attention_required,
                    'patient_ids': [],
                    'patients_json': {},
                },
            )
        except UniqueProperty as e:
            raise e

    def createPatientProtocolRel(
        self,
        patient_id: Any,
        name_protocol: Any,
        attention_required: Any,
    ) -> None:
        try:
            self.searchNodes(
                name=patient_id,
                node_type='NeoPatient',
            ).to_protocol.connect(
                self.searchNodes(name=name_protocol, node_type='NeoProtocol'),
                {'attention_required': attention_required},
            )
        except NeomodelException as e:
            raise e

    def createProtocolPatientRel(
        self,
        patient_id: Any,
        name_protocol: Any,
    ) -> None:
        try:
            self.searchNodes(
                name=name_protocol,
                node_type='NeoProtocol',
            ).backto_patient.connect(
                self.searchNodes(
                    name=patient_id,
                    node_type='NeoPatient',
                ),
            )
        except NeomodelException as e:
            raise e

    def createProtocolDiseaseRel(
        self,
        name_protocol: Any,
        patient_id: Any,
        name_disease: Any,
        attention_required: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(
                name=name_protocol,
                node_type='NeoProtocol',
            )
            node_finish = self.searchNodes(
                name=name_disease,
                node_type='NeoDisease',
            )
            if node_start and (len(node_start.to_disease.all_relationships(node_finish))) < 1:
                node_start.to_disease.connect(
                    node_finish,
                    {
                        'patient_id': patient_id,
                        'protocol_name': name_protocol,
                        'attention': attention_required,
                    },
                )
        except NeomodelException as e:
            raise e

    def createProtocolSymptomFeatureRel(
        self,
        name_protocol: Any,
        patient_id: Any,
        name_symptomfeature: Any,
        attention_required: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(
                name=name_protocol,
                node_type='NeoProtocol',
            )
            node_finish = self.searchNodes(
                name=name_symptomfeature,
                node_type='NeoSymptomFeature',
            )
            if node_start and (len(node_start.to_symptomfeature.all_relationships(node_finish))) < 1:
                node_start.to_symptomfeature.connect(
                    node_finish,
                    {
                        'patient_id': patient_id,
                        'protocol_name': name_protocol,
                        'attention': attention_required,
                    },
                )
        except NeomodelException as e:
            raise e

    def createProtocolInspectionFeatureRel(
        self,
        name_protocol: Any,
        patient_id: Any,
        name_inspectionfeature: Any,
        attention_required: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(
                name=name_protocol,
                node_type='NeoProtocol',
            )
            node_finish = self.searchNodes(
                name=name_inspectionfeature,
                node_type='NeoInspectionFeature',
            )
            if node_start and (len(node_start.to_inspectionfeature.all_relationships(node_finish))) < 1:
                node_start.to_inspectionfeature.connect(
                    node_finish,
                    {
                        'patient_id': patient_id,
                        'protocol_name': name_protocol,
                        'attention': attention_required,
                    },
                )
        except NeomodelException as e:
            raise e

    def create_relation_protocol_med_service(
        self,
        name_protocol: Any,
        patient_id: Any,
        med_service_name: Any,
        attention_required: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(
                name=name_protocol,
                node_type='NeoProtocol',
            )
            node_finish = self.searchNodes(
                name=med_service_name,
                node_type='NeoMedServiceFeature',
            )
            if node_start and (len(node_start.to_med_service.all_relationships(node_finish))) < 1:
                node_start.to_med_service.connect(
                    node_finish,
                    {
                        'patient_id': patient_id,
                        'protocol_name': name_protocol,
                        'attention': attention_required,
                    },
                )
        except NeomodelException as e:
            raise e

    def createProtocolTherapyFeatureRel(
        self,
        name_protocol: Any,
        patient_id: Any,
        name_therapyfeature: Any,
        attention_required: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(
                name=name_protocol,
                node_type='NeoProtocol',
            )
            node_finish = self.searchNodes(
                name=name_therapyfeature,
                node_type='NeoTherapyFeature',
            )
            if node_start and (len(node_start.to_therapyfeature.all_relationships(node_finish))) < 1:
                node_start.to_therapyfeature.connect(
                    node_finish,
                    {
                        'patient_id': patient_id,
                        'protocol_name': name_protocol,
                        'attention': attention_required,
                    },
                )
        except NeomodelException as e:
            raise e

    def createorganNode(
        self,
        name: Any,
    ) -> None:
        try:
            # NeoOrgan(value=name, patients_ids=[], patients_json={}).save()
            NeoOrgan.get_or_create(
                {'name': name, 'patients_ids': [], 'patients_json': {}},
            )
        except UniqueProperty as e:
            raise e

    def createorganstructureNode(
        self,
        name: Any,
    ) -> None:
        try:
            NeoOrganStructure.get_or_create(
                {'name': name, 'patients_ids': [], 'patients_json': {}},
            )
        except UniqueProperty as e:
            raise e

    def createanomalityNode(
        self,
        name: Any,
        attention_required: bool = False,
    ) -> None:
        try:
            NeoAnomality.get_or_create(
                {
                    'name': name,
                    'attention_required': attention_required,
                    'patients_ids': [],
                    'patients_json': {},
                },
            )
        except UniqueProperty as e:
            raise e

    def createfeaturestructureNode(
        self,
        name: Any,
        attention_required: Any,
    ) -> None:
        try:
            NeoFeatureStructure.get_or_create(
                {
                    'name': name,
                    'attention_required': attention_required,
                    'patients_ids': [],
                    'patients_json': {},
                },
            )
        except UniqueProperty as e:
            raise e

    def createanatomicalfeatureNode(
        self,
        name: Any,
    ) -> None:
        try:
            NeoAnatomicalFeature.get_or_create({'name': name, 'patients_ids': [], 'patients_json': {}})
        except UniqueProperty as e:
            raise e

    def createanatomicalvalueNode(
        self,
        name: Any,
        attention_required: bool = False,
    ) -> None:
        try:
            NeoAnatomicalValue.get_or_create(
                {
                    'name': name,
                    'attention_required': attention_required,
                    'patients_ids': [],
                    'patients_json': {},
                },
            )
        except UniqueProperty as e:
            raise e

    def createbodystructureNode(
        self,
        name: Any,
        attention_required: bool = False,
    ) -> None:
        try:
            NeoBodyStructure.get_or_create(
                {
                    'name': name,
                    'attention_required': attention_required,
                    'patients_ids': [],
                    'patients_json': {},
                },
            )
        except UniqueProperty as e:
            raise e

    def createbodyfluidsNode(
        self,
        name: Any,
        attention_required: bool = False,
    ) -> None:
        try:
            NeoBodyFluids.get_or_create(
                {
                    'name': name,
                    'attention_required': attention_required,
                    'patients_ids': [],
                    'patients_json': {},
                },
            )
        except UniqueProperty as e:
            raise e

    def createsymptomfeatureNode(
        self,
        name: Any,
        attention_required: bool = False,
    ) -> None:
        try:
            NeoSymptomFeature.get_or_create(
                {
                    'name': name,
                    'attention_required': attention_required,
                    'patients_ids': [],
                    'patients_json': {},
                },
            )
        except UniqueProperty as e:
            raise e

    def createsymptomvalueNode(
        self,
        name: Any,
        attention_required: bool = False,
    ) -> None:
        try:
            NeoSymptomValue.get_or_create(
                {
                    'name': name,
                    'attention_required': attention_required,
                    'patients_ids': [],
                    'patients_json': {},
                },
            )
        except UniqueProperty as e:
            raise e

    def createinspectionfeatureNode(
        self,
        name: Any,
        attention_required: Any,
    ) -> None:
        try:
            NeoInspectionFeature.get_or_create(
                {
                    'name': name,
                    'attention_required': attention_required,
                    'patients_ids': [],
                    'patients_json': {},
                },
            )
        except UniqueProperty as e:
            raise e

    def createinspectionvalueNode(
        self,
        name: Any,
        attention_required: Any,
    ) -> None:
        try:
            NeoInspectionValue.get_or_create(
                {
                    'name': name,
                    'attention_required': attention_required,
                    'patients_ids': [],
                    'patients_json': {},
                },
            )
        except UniqueProperty as e:
            raise e

    def create_med_service_feature_node(
        self,
        name: Any,
        attention_required: bool = False,
    ) -> None:
        try:
            NeoMedServiceFeature.get_or_create(
                {
                    'name': name,
                    'attention_required': attention_required,
                    'patients_ids': [],
                    'patients_json': {},
                },
            )
        except UniqueProperty as e:
            raise e

    def create_med_service_value_node(
        self,
        name: Any,
        attention_required: bool = False,
    ) -> None:
        try:
            NeoMedServiceValue.get_or_create(
                {
                    'name': name,
                    'attention_required': attention_required,
                    'patients_ids': [],
                    'patients_json': {},
                },
            )
        except UniqueProperty as e:
            raise e

    def createtherapyfeatureNode(
        self,
        name: Any,
        attention_required: bool = False,
    ) -> None:
        try:
            NeoTherapyFeature.get_or_create(
                {
                    'name': name,
                    'attention_required': attention_required,
                    'patients_ids': [],
                    'patients_json': {},
                },
            )
        except UniqueProperty as e:
            raise e

    def createtherapyvalueNode(
        self,
        name: Any,
        attention_required: bool = False,
    ) -> None:
        try:
            NeoTherapyValue.get_or_create(
                {
                    'name': name,
                    'attention_required': attention_required,
                    'patients_ids': [],
                    'patients_json': {},
                },
            )
        except UniqueProperty as e:
            raise e

    def createpatientanthropometryfeatureNode(
        self,
        name: Any,
        attention_required: Any,
    ) -> None:
        try:
            NeoPatientAnthropometryFeature.get_or_create(
                {
                    'name': name,
                    'attention_required': attention_required,
                    'patients_ids': [],
                    'patients_json': {},
                },
            )
        except UniqueProperty as e:
            raise e

    def createpatientanthropometryvalueNode(
        self,
        name: Any,
        attention_required: Any,
    ) -> None:
        try:
            NeoPatientAnthropometryValue.get_or_create(
                {
                    'name': name,
                    'attention_required': attention_required,
                    'patients_ids': [],
                    'patients_json': {},
                },
            )
        except UniqueProperty as e:
            raise e

    def createpatientdemographyfeatureNode(
        self,
        name: Any,
        attention_required: Any,
    ) -> None:
        try:
            NeoPatientDemographyFeature.get_or_create(
                {
                    'name': name,
                    'attention_required': attention_required,
                    'patients_ids': [],
                    'patients_json': {},
                },
            )
        except UniqueProperty as e:
            raise e

    def createpatientdemographyvalueNode(
        self,
        name: Any,
        attention_required: Any,
    ) -> None:
        try:
            NeoPatientDemographyValue.get_or_create(
                {
                    'name': name,
                    'attention_required': attention_required,
                    'patients_ids': [],
                    'patients_json': {},
                },
            )
        except UniqueProperty as e:
            raise e

    def create_neomkb10_level_01_node(
        self,
        name: Any,
        current_id: Any,
        parent_id: Any,
        treecode: Any,
        level: Any,
    ) -> None:
        try:
            NeoMkb10_level_01.get_or_create(
                {
                    'name': name,
                    'current_id': current_id,
                    'parent_id': parent_id,
                    'treecode': treecode,
                    'level': level,
                },
            )
        except UniqueProperty as e:
            raise e

    def create_neomkb10_level_02_node(
        self,
        name: Any,
        current_id: Any,
        parent_id: Any,
        treecode: Any,
        level: Any,
    ) -> None:
        try:
            NeoMkb10_level_02.get_or_create(
                {
                    'name': name,
                    'current_id': current_id,
                    'parent_id': parent_id,
                    'treecode': treecode,
                    'level': level,
                },
            )
        except UniqueProperty as e:
            raise e

    def create_neomkb10_level_03_node(
        self,
        name: Any,
        current_id: Any,
        parent_id: Any,
        treecode: Any,
        level: Any,
    ) -> None:
        try:
            NeoMkb10_level_03.get_or_create(
                {
                    'name': name,
                    'current_id': current_id,
                    'parent_id': parent_id,
                    'treecode': treecode,
                    'level': level,
                },
            )
        except UniqueProperty as e:
            raise e

    def create_neomkb10_level_04_node(
        self,
        name: Any,
        current_id: Any,
        parent_id: Any,
        treecode: Any,
        level: Any,
    ) -> None:
        try:
            NeoMkb10_level_04.get_or_create(
                {
                    'name': name,
                    'current_id': current_id,
                    'parent_id': parent_id,
                    'treecode': treecode,
                    'level': level,
                },
            )
        except UniqueProperty as e:
            raise e

    def create_neomkb10_level_05_node(
        self,
        name: Any,
        current_id: Any,
        parent_id: Any,
        treecode: Any,
        level: Any,
    ) -> None:
        try:
            NeoMkb10_level_05.get_or_create(
                {
                    'name': name,
                    'current_id': current_id,
                    'parent_id': parent_id,
                    'treecode': treecode,
                    'level': level,
                },
            )
        except UniqueProperty as e:
            raise e

    def create_neomkb10_level_06_node(
        self,
        name: Any,
        current_id: Any,
        parent_id: Any,
        treecode: Any,
        level: Any,
    ) -> None:
        try:
            NeoMkb10_level_06.get_or_create(
                {
                    'name': name,
                    'current_id': current_id,
                    'parent_id': parent_id,
                    'treecode': treecode,
                    'level': level,
                },
            )
        except UniqueProperty as e:
            raise e

    def createMKB10_2_1_Rel(
        self,
        treecode_2: Any,
        treecode_1: Any,
        status: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(
                name=treecode_2,
                node_type='NeoMkb10_level_02',
            )
            node_finish = self.searchNodes(
                name=treecode_1,
                node_type='NeoMkb10_level_01',
            )
            if node_start and (len(node_start.backto_neomkb10_level_01.all_relationships(node_finish))) < 1:
                node_start.backto_neomkb10_level_01.connect(
                    node_finish,
                    {
                        'status': status,
                    },
                )
                node_finish.to_neomkb10_level_02.connect(
                    node_start,
                    {
                        'status': status,
                    },
                )
        except NeomodelException as e:
            raise e

    def createMKB10_3_2_Rel(
        self,
        treecode_3: Any,
        treecode_2: Any,
        status: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(
                name=treecode_3,
                node_type='NeoMkb10_level_03',
            )
            node_finish = self.searchNodes(
                name=treecode_2,
                node_type='NeoMkb10_level_02',
            )
            if node_start and (len(node_start.backto_neomkb10_level_02.all_relationships(node_finish))) < 1:
                node_start.backto_neomkb10_level_02.connect(
                    node_finish,
                    {
                        'status': status,
                    },
                )
                node_finish.to_neomkb10_level_03.connect(
                    node_start,
                    {
                        'status': status,
                    },
                )
        except NeomodelException as e:
            raise e

    def createMKB10_4_3_Rel(
        self,
        treecode_4: Any,
        treecode_3: Any,
        status: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(
                name=treecode_4,
                node_type='NeoMkb10_level_04',
            )
            node_finish = self.searchNodes(
                name=treecode_3,
                node_type='NeoMkb10_level_03',
            )
            if node_start and (len(node_start.backto_neomkb10_level_03.all_relationships(node_finish))) < 1:  # 3041
                node_start.backto_neomkb10_level_03.connect(
                    node_finish,
                    {
                        'status': status,
                    },
                )
                node_finish.to_neomkb10_level_04.connect(
                    node_start,
                    {
                        'status': status,
                    },
                )
        except NeomodelException as e:
            raise e

    def createMKB10_5_4_Rel(
        self,
        treecode_5: Any,
        treecode_4: Any,
        status: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(
                name=treecode_5,
                node_type='NeoMkb10_level_05',
            )
            node_finish = self.searchNodes(
                name=treecode_4,
                node_type='NeoMkb10_level_04',
            )
            if node_start and (len(node_start.backto_neomkb10_level_04.all_relationships(node_finish))) < 1:
                node_start.backto_neomkb10_level_04.connect(
                    node_finish,
                    {
                        'status': status,
                    },
                )
                node_finish.to_neomkb10_level_05.connect(
                    node_start,
                    {
                        'status': status,
                    },
                )
        except NeomodelException as e:
            raise e

    def createMKB10_6_5_Rel(
        self,
        treecode_6: Any,
        treecode_5: Any,
        status: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(
                name=treecode_6,
                node_type='NeoMkb10_level_06',
            )
            node_finish = self.searchNodes(
                name=treecode_5,
                node_type='NeoMkb10_level_05',
            )
            if node_start and (len(node_start.backto_neomkb10_level_05.all_relationships(node_finish))) < 1:
                node_start.backto_neomkb10_level_05.connect(
                    node_finish,
                    {
                        'status': status,
                    },
                )
                node_finish.to_neomkb10_level_06.connect(
                    node_start,
                    {
                        'status': status,
                    },
                )
        except NeomodelException as e:
            raise e

    def createTherapyFeatureTherapyValueRel(
        self,
        name_therapyfeature: Any,
        patient_id: Any,
        name_therapyvalue: Any,
        name_protocol: Any,
        feedback: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(
                name=name_therapyfeature,
                node_type='NeoTherapyFeature',
            )
            node_finish = self.searchNodes(
                name=name_therapyvalue,
                node_type='NeoTherapyValue',
            )
            if (len(node_start.to_therapyvalue.all_relationships(node_finish))) < 1:
                node_start.to_therapyvalue.connect(
                    node_finish,
                    {
                        'patient_id': patient_id,
                        'protocol_name': name_protocol,
                        'attention': feedback,
                    },
                )
        except NeomodelException as e:
            raise e

    def create_relation_med_service_feature_value(
        self,
        med_service_name: Any,
        patient_id: Any,
        med_service_value: Any,
        name_protocol: Any,
        feedback: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(
                name=med_service_name,
                node_type='NeoMedServiceFeature',
            )
            node_finish = self.searchNodes(
                name=med_service_value,
                node_type='NeoMedServiceValue',
            )
            if (len(node_start.to_med_service_value.all_relationships(node_finish))) < 1:
                node_start.to_med_service_value.connect(
                    node_finish,
                    {
                        'patient_id': patient_id,
                        'protocol_name': name_protocol,
                        'attention': feedback,
                    },
                )
        except NeomodelException as e:
            raise e

    def createInspectionFeatureInspectionValueRel(
        self,
        name_inspectionfeature: Any,
        patient_id: Any,
        name_inspectionvalue: Any,
        name_protocol: Any,
        feedback: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(
                name=name_inspectionfeature,
                node_type='NeoInspectionFeature',
            )
            node_finish = self.searchNodes(
                name=name_inspectionvalue,
                node_type='NeoInspectionValue',
            )
            if (len(node_start.to_inspectionvalue.all_relationships(node_finish))) < 1:
                node_start.to_inspectionvalue.connect(
                    node_finish,
                    {
                        'patient_id': patient_id,
                        'protocol_name': name_protocol,
                        'attention': feedback,
                    },
                )
        except NeomodelException as e:
            raise e

    def createSymptomFeatureSymptomValueRel(
        self,
        name_symptomfeature: Any,
        patient_id: Any,
        name_symptomvalue: Any,
        name_protocol: Any,
        feedback: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(
                name=name_symptomfeature,
                node_type='NeoSymptomFeature',
            )
            node_finish = self.searchNodes(
                name=name_symptomvalue,
                node_type='NeoSymptomValue',
            )
            if (len(node_start.to_symptomvalue.all_relationships(node_finish))) < 1:
                node_start.to_symptomvalue.connect(
                    node_finish,
                    {
                        'patient_id': patient_id,
                        'protocol_name': name_protocol,
                        'attention': feedback,
                    },
                )
        except NeomodelException as e:
            raise e

    def createPatientAnthropometryFeaturePatientAnthropometryValueRel(
        self,
        name_patientanthropometryfeature: Any,
        patient_id: Any,
        name_patientanthropometryvalue: Any,
        name_protocol: Any,
        feedback: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(
                name=name_patientanthropometryfeature,
                node_type='NeoPatientAnthropometryFeature',
            )
            node_finish = self.searchNodes(
                name=name_patientanthropometryvalue,
                node_type='NeoPatientAnthropometryValue',
            )
            if (len(node_start.to_patientanthropometryvalue.all_relationships(node_finish))) < 1:
                node_start.to_patientanthropometryvalue.connect(
                    node_finish,
                    {
                        'patient_id': patient_id,
                        'protocol_name': name_protocol,
                        'attention': feedback,
                    },
                )
        except NeomodelException as e:
            raise e

    def createPatientDemographyFeaturePatientDemographyValueRel(
        self,
        name_patientdemographyfeature: Any,
        patient_id: Any,
        name_patientdemographyvalue: Any,
        name_protocol: Any,
        feedback: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(
                name=name_patientdemographyfeature,
                node_type='NeoPatientDemographyFeature',
            )
            node_finish = self.searchNodes(
                name=name_patientdemographyvalue,
                node_type='NeoPatientDemographyValue',
            )
            if (len(node_start.to_patientdemographyvalue.all_relationships(node_finish))) < 1:
                node_start.to_patientdemographyvalue.connect(
                    node_finish,
                    {
                        'patient_id': patient_id,
                        'protocol_name': name_protocol,
                        'attention': feedback,
                    },
                )
        except NeomodelException as e:
            raise e

    def createPatientOrganRel(
        self,
        name_organ: Any,
        patient_id: Any,
        name_protocol: Any,
        feedback: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(
                name=patient_id,
                node_type='NeoPatient',
            )
            node_finish = self.searchNodes(
                name=name_organ,
                node_type='NeoOrgan',
            )
            if (len(node_start.to_organ.all_relationships(node_finish))) < 1:
                node_start.to_organ.connect(
                    node_finish,
                    {
                        'patient_id': patient_id,
                        'protocol_name': name_protocol,
                        'attention': feedback,
                    },
                )
        except NeomodelException as e:
            raise e

    def createOrganProtocolRel(
        self,
        name_organ: Any,
        patient_id: Any,
        name_protocol: Any,
        feedback: Any,
    ) -> None:
        try:
            self.searchNodes(
                name=name_organ,
                node_type='NeoOrgan',
            ).backto_protocol.connect(
                self.searchNodes(
                    name=name_protocol,
                    node_type='NeoProtocol',
                ),
                {
                    'patient_id': patient_id,
                    'protocol_name': name_protocol,
                    'attention': feedback,
                },
            )
        except NeomodelException as e:
            raise e

    def createOrganPatientRel(
        self,
        name_organ: Any,
        patient_id: Any,
        name_protocol: Any,
        feedback: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(
                name=name_organ,
                node_type='NeoOrgan',
            )
            node_finish = self.searchNodes(
                name=patient_id,
                node_type='NeoPatient',
            )
            if (len(node_start.backto_patient.all_relationships(node_finish))) < 1:
                node_start.backto_patient.connect(
                    node_finish,
                    {
                        'patient_id': patient_id,
                        'protocol_name': name_protocol,
                        'attention': feedback,
                    },
                )
        except NeomodelException as e:
            raise e

    def createOrganRel(
        self,
        name_protocol: Any,
        name_organ: Any,
        patient_id: Any,
        attention_required: Any,
        feedback: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(
                name=name_protocol,
                node_type='NeoProtocol',
            )
            node_finish = self.searchNodes(
                name=name_organ,
                node_type='NeoOrgan',
            )
            if attention_required:
                node_finish.attention_required_count += 1
                node_finish.save()
            node_start_patient_id = node_start.patient_id
            if node_start_patient_id not in node_finish.patients_ids:
                node_finish.patients_ids.append(node_start.patient_id)
                node_finish.save()
            node_start.to_organ.connect(node_finish, {'patient_id': node_start_patient_id})
            if feedback:
                self.createOrganPatientRel(
                    name_organ=name_organ,
                    patient_id=patient_id,
                    name_protocol=name_protocol,
                    feedback=feedback,
                )
                self.createOrganProtocolRel(
                    name_organ=name_organ,
                    patient_id=patient_id,
                    name_protocol=name_protocol,
                    feedback=feedback,
                )
        except NeomodelException as e:
            raise e

    def createOrganStructureProtocolRel(
        self,
        name_organstructure: Any,
        patient_id: Any,
        name_protocol: Any,
        feedback: Any,
    ) -> None:
        try:
            self.searchNodes(name=name_organstructure, node_type='NeoOrganStructure').backto_protocol.connect(
                self.searchNodes(name=name_protocol, node_type='NeoProtocol'),
                {
                    'patient_id': patient_id,
                    'protocol_name': name_protocol,
                    'attention': feedback,
                },
            )
        except NeomodelException as e:
            raise e

    def createOrganStructurePatientRel(
        self,
        name_organstructure: Any,
        patient_id: Any,
        name_protocol: Any,
        feedback: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(name=name_organstructure, node_type='NeoOrganStructure')
            node_finish = self.searchNodes(
                name=patient_id,
                node_type='NeoPatient',
            )
            if (len(node_start.backto_patient.all_relationships(node_finish))) < 1:
                node_start.backto_patient.connect(
                    node_finish,
                    {
                        'patient_id': patient_id,
                        'protocol_name': name_protocol,
                        'attention': feedback,
                    },
                )
        except NeomodelException as e:
            raise e

    def createOrganStructureRel(
        self,
        name_organ: Any,
        name_organstructure: Any,
        patient_id: Any,
        name_protocol: Any,
        feedback: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(
                name=name_organ,
                node_type='NeoOrgan',
            )
            node_finish = self.searchNodes(
                name=name_organstructure,
                node_type='NeoOrganStructure',
            )
            patient_id = patient_id
            if patient_id not in node_finish.patients_ids:
                node_finish.patients_ids.append(patient_id)
                node_finish.save()
            if (len(node_start.to_organstructure.all_relationships(node_finish))) < 1:
                node_start.to_organstructure.connect(node_finish, {'patient_id': patient_id})
            if feedback:
                self.createOrganStructurePatientRel(
                    name_organstructure=name_organstructure,
                    patient_id=patient_id,
                    name_protocol=name_protocol,
                    feedback=feedback,
                )
                self.createOrganStructureProtocolRel(
                    name_organstructure=name_organstructure,
                    patient_id=patient_id,
                    name_protocol=name_protocol,
                    feedback=feedback,
                )
        except NeomodelException as e:
            raise e

    def createAnatomicalFeatureOrganRel(
        self,
        name_anatomicalfeature: Any,
        name_organ: Any,
        patient_id: Any,
        name_protocol: Any,
        feedback: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(
                name=name_anatomicalfeature,
                node_type='NeoAnatomicalFeature',
            )
            node_finish = self.searchNodes(
                name=name_organ,
                node_type='NeoOrgan',
            )
            if (len(node_start.backto_organ.all_relationships(node_finish))) < 1:
                node_start.backto_organ.connect(
                    node_finish,
                    {
                        'patient_id': patient_id,
                        'protocol_name': name_protocol,
                        'attention': feedback,
                    },
                )
        except NeomodelException as e:
            raise e

    def createAnatomicalFeatureProtocolRel(
        self,
        name_anatomicalfeature: Any,
        patient_id: Any,
        name_protocol: Any,
        feedback: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(
                name=name_anatomicalfeature,
                node_type='NeoAnatomicalFeature',
            )
            node_finish = self.searchNodes(
                name=name_protocol,
                node_type='NeoProtocol',
            )
            if (len(node_start.backto_protocol.all_relationships(node_finish))) < 1:
                node_start.backto_protocol.connect(
                    node_finish,
                    {
                        'patient_id': patient_id,
                        'protocol_name': name_protocol,
                        'attention': feedback,
                    },
                )
        except NeomodelException as e:
            raise e

    def createAnatomicalFeaturePatientRel(
        self,
        name_anatomicalfeature: Any,
        patient_id: Any,
        name_protocol: Any,
        feedback: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(
                name=name_anatomicalfeature,
                node_type='NeoAnatomicalFeature',
            )
            node_finish = self.searchNodes(
                name=patient_id,
                node_type='NeoPatient',
            )
            if (len(node_start.backto_patient.all_relationships(node_finish))) < 1:
                node_start.backto_patient.connect(
                    node_finish,
                    {
                        'patient_id': patient_id,
                        'protocol_name': name_protocol,
                        'attention': feedback,
                    },
                )
        except NeomodelException as e:
            raise e

    def createAnatomicalFeatureRel(
        self,
        name_organ: Any,
        name_structure: Any,
        name_anatomicalfeature: Any,
        patient_id: Any,
        name_protocol: Any,
        previous_node: Any,
        feedback: Any,
    ) -> None:
        try:
            patient_id = patient_id
            name_protocol = name_protocol
            if previous_node == 'NeoOrganStructure':
                node_start = self.searchNodes(name=name_structure, node_type='NeoOrganStructure')
            elif previous_node == 'NeoFeatureStructure':
                node_start = self.searchNodes(name=name_structure, node_type='NeoFeatureStructure')
            node_finish = self.searchNodes(
                name=name_anatomicalfeature,
                node_type='NeoAnatomicalFeature',
            )
            if node_finish.patients_json.get(str(patient_id)) is None:
                node_finish.patients_json[str(patient_id)] = []
            protocols_uuids = node_finish.patients_json[str(patient_id)]
            protocols_uuids.append(name_protocol)
            node_finish.patients_json[str(patient_id)] = protocols_uuids
            node_finish.save()
            if patient_id not in node_finish.patients_ids:
                node_finish.patients_ids.append(patient_id)
                node_finish.save()
            if (len(node_start.to_anatomicalfeature.all_relationships(node_finish))) < 1:
                node_start.to_anatomicalfeature.connect(
                    node_finish,
                    {'patient_id': patient_id},
                )
            if feedback:
                self.createAnatomicalFeaturePatientRel(
                    name_anatomicalfeature=name_anatomicalfeature,
                    patient_id=patient_id,
                    name_protocol=name_protocol,
                    feedback=feedback,
                )
                self.createAnatomicalFeatureProtocolRel(
                    name_anatomicalfeature=name_anatomicalfeature,
                    patient_id=patient_id,
                    name_protocol=name_protocol,
                    feedback=feedback,
                )
                self.createAnatomicalFeatureOrganRel(
                    name_anatomicalfeature=name_anatomicalfeature,
                    name_organ=name_organ,
                    patient_id=patient_id,
                    name_protocol=name_protocol,
                    feedback=feedback,
                )
        except NeomodelException as e:
            raise e

    def creatAnatomicalValueProtocolRel(
        self,
        name_anatomicalvalue: Any,
        patient_id: Any,
        name_protocol: Any,
        feedback: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(
                name=name_anatomicalvalue,
                node_type='NeoAnatomicalValue',
            )
            node_finish = self.searchNodes(
                name=name_protocol,
                node_type='NeoProtocol',
            )
            if (len(node_start.backto_protocol.all_relationships(node_finish))) < 1:
                node_start.backto_protocol.connect(
                    node_finish,
                    {
                        'patient_id': patient_id,
                        'protocol_name': name_protocol,
                        'attention': feedback,
                    },
                )
        except NeomodelException as e:
            raise e

    def createAnatomicalValuePatientRel(
        self,
        name_anatomicalvalue: Any,
        patient_id: Any,
        name_protocol: Any,
        attention_required: Any,
        feedback: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(
                name=name_anatomicalvalue,
                node_type='NeoAnatomicalValue',
            )
            node_finish = self.searchNodes(
                name=patient_id,
                node_type='NeoPatient',
            )
            #    if feedback:
            # # (len(node_start.backto_patient.all_relationships(node_finish))) < 1:
            if attention_required or (len(node_start.backto_patient.all_relationships(node_finish))) < 1:
                node_start.backto_patient.connect(
                    node_finish,
                    {
                        'patient_id': patient_id,
                        'protocol_name': name_protocol,
                        'attention': attention_required,
                    },
                )
        except NeomodelException as e:
            raise e

    def createAnatomicalValueRel(
        self,
        name_organ: Any,
        name_organstructure: Any,
        name_anatomicalfeature: Any,
        name_anatomicalvalue: Any,
        patient_id: Any,
        name_protocol: Any,
        attention_required: Any,
        feedback: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(
                name=name_anatomicalfeature,
                node_type='NeoAnatomicalFeature',
            )
            node_finish = self.searchNodes(
                name=name_anatomicalvalue,
                node_type='NeoAnatomicalValue',
            )
            patient_id = patient_id
            if type(name_anatomicalvalue) is not int:
                node_finish.attention_required = attention_required
                if patient_id not in node_finish.patients_ids:
                    node_finish.patients_ids.append(patient_id)
                    node_finish.save()
                if len(node_start.to_anatomicalvalue.all_relationships(node_finish)) < 1:
                    node_start.to_anatomicalvalue.connect(
                        node_finish,
                        {'patient_id': patient_id},
                    )
            if feedback:
                self.createAnatomicalValuePatientRel(
                    name_anatomicalvalue=name_anatomicalvalue,
                    patient_id=patient_id,
                    name_protocol=name_protocol,
                    attention_required=attention_required,
                    feedback=feedback,
                )
                self.createAnatomicalValuePatientRel(
                    name_anatomicalvalue=name_anatomicalvalue,
                    patient_id=patient_id,
                    name_protocol=name_protocol,
                    attention_required=attention_required,
                    feedback=feedback,
                )
        except NeomodelException as e:
            raise e

    def createFeatureStructurePatientRel(
        self,
        name_featurestructure: Any,
        patient_id: Any,
        name_protocol: Any,
        feedback: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(name=name_featurestructure, node_type='NeoFeatureStructure')
            node_finish = self.searchNodes(
                name=patient_id,
                node_type='NeoPatient',
            )
            if (len(node_start.backto_patient.all_relationships(node_finish))) < 1:  # feedback or (len())
                node_start.backto_patient.connect(
                    node_finish,
                    {
                        'patient_id': patient_id,
                        'protocol_name': name_protocol,
                        'attention': feedback,
                    },
                )
        except NeomodelException as e:
            raise e

    def createFeatureStructureRel(
        self,
        name_anomality: Any,
        name_featurestructure: Any,
        name_anatomicalfeature: Any,
        patient_id: Any,
        name_protocol: Any,
        attention_required: Any,
        feedback: Any,
    ) -> None:
        """
        name_anomality:\n,
        name_featurestructure:\n,
        name_anatomicalfeature:\n,
        patient_id:\n,
        name_protocol:\n,
        attention_required:\n,
        feedback:
        """
        try:
            node_start = self.searchNodes(name=name_anomality, node_type='NeoAnomality')
            node_finish = self.searchNodes(name=name_featurestructure, node_type='NeoFeatureStructure')
            if node_start and node_finish:
                patient_id = patient_id
                #           if (type(name_anatomicalvalue) is not int):
                node_finish.attention_required = attention_required
                if patient_id not in node_finish.patients_ids:
                    node_finish.patients_ids.append(patient_id)
                    node_finish.save()
                if len(node_start.to_featurestructure.all_relationships(node_finish)) < 1:
                    node_start.to_featurestructure.connect(node_finish, {'patient_id': patient_id})
            if feedback:
                self.createFeatureStructurePatientRel(
                    name_featurestructure=name_featurestructure,
                    patient_id=patient_id,
                    name_protocol=name_protocol,
                    feedback=feedback,
                )
                # self.createAnatomicalValueProtocolRel(
                #     name_anatomicalvalue=name_anatomicalvalue,  # to_do
                #     patient_id=patient_id,
                #     name_protocol=name_protocol,
                #     feedback=feedback,
                # )
        except NeomodelException as e:
            raise e

    def createAnomalityRel(
        self,
        name_organstructure: Any,
        name_anomality: Any,
        patient_id: Any,
        name_protocol: Any,
        feedback: Any,
    ) -> None:
        try:
            node_start = self.searchNodes(name=name_organstructure, node_type='NeoOrganStructure')
            node_finish = self.searchNodes(name=name_anomality, node_type='NeoAnomality')
            if node_start and node_finish:
                patient_id = patient_id
                if patient_id not in node_finish.patients_ids:
                    node_finish.patients_ids.append(patient_id)
                    node_finish.save()
                if (len(node_start.to_anomality.all_relationships(node_finish))) < 1:
                    node_start.to_anomality.connect(node_finish, {'patient_id': patient_id})
            # if feedback:
            #     self.createOrganStructurePatientRel(
            #         name_organstructure=name_organstructure,
            #         patient_id=patient_id, name_protocol=name_protocol,
            #         feedback=feedback,
            #     )
            #     self.createOrganStructureProtocolRel(
            #         name_organstructure=name_organstructure,
            #         patient_id=patient_id,
            #         name_protocol=name_protocol,
            #         feedback=feedback,
            #     )
        except NeomodelException as e:
            raise e

    def createFeatureStructureAnatomicalFeatureRel(
        self,
        name_organ: Any,
        name_featurestructure: Any,
        name_anatomicalfeature: Any,
        patient_id: Any,
        name_protocol: Any,
        feedback: Any,
    ) -> None:
        """
        name_featurestructure:\n
        name_anatomicalfeature:
        """
        try:
            node_start = self.searchNodes(name=name_featurestructure, node_type='NeoFeatureStructure')
            node_finish = self.searchNodes(
                name=name_anatomicalfeature,
                node_type='NeoAnatomicalFeature',
            )
            if node_finish is None:
                self.createanatomicalfeatureNode(name=name_anatomicalfeature)
                self.createAnatomicalFeatureRel(
                    name_organ=name_organ,
                    name_structure=name_featurestructure,
                    name_anatomicalfeature=name_anatomicalfeature,
                    patient_id=patient_id,
                    name_protocol=name_protocol,
                    previous_node='NeoFeatureStructure',
                    feedback=feedback,
                )
                node_finish = self.searchNodes(
                    name=name_anatomicalfeature,
                    node_type='NeoAnatomicalFeature',
                )
            if (len(node_start.to_anatomicalfeature.all_relationships(node_finish))) < 1:
                node_start.to_anatomicalfeature.connect(
                    node_finish,
                    {
                        'patient_id': patient_id,
                        'protocol_name': name_protocol,
                        'attention': feedback,
                    },
                )
        except NeomodelException as e:
            raise e

    def searchNodes(
        self,
        name: Any,
        node_type: Any,
    ) -> Any:
        match node_type:
            case 'NeoPatient':
                try:
                    node = NeoPatient.nodes.get(name=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoProtocol':
                try:
                    node = NeoProtocol.nodes.get(name=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoProtocolFeature':
                try:
                    node = NeoProtocolFeature.nodes.get(name=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoDisease':
                try:
                    node = NeoDisease.nodes.get(name=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoPatientAnthropometryFeature':
                try:
                    node = NeoPatientAnthropometryFeature.nodes.get(name=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoPatientAnthropometryValue':
                try:
                    node = NeoPatientAnthropometryValue.nodes.get(name=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoPatientDemographyFeature':
                try:
                    node = NeoPatientDemographyFeature.nodes.get(name=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoPatientDemographyValue':
                try:
                    node = NeoPatientDemographyValue.nodes.get(name=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoOrgan':
                try:
                    node = NeoOrgan.nodes.get(name=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoOrganStructure':
                try:
                    node = NeoOrganStructure.nodes.get(name=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoAnomality':
                try:
                    node = NeoAnomality.nodes.get(name=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoFeatureStructure':
                try:
                    node = NeoFeatureStructure.nodes.get(name=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoAnatomicalFeature':
                try:
                    node = NeoAnatomicalFeature.nodes.get(name=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoAnatomicalValue':
                try:
                    node = NeoAnatomicalValue.nodes.get(name=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoBodyStructure':
                try:
                    node = NeoBodyStructure.nodes.get(name=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoBodyFluids':
                try:
                    node = NeoBodyFluids.nodes.get(name=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoSymptomFeature':
                try:
                    node = NeoSymptomFeature.nodes.get(name=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoSymptomValue':
                try:
                    node = NeoSymptomValue.nodes.get(name=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoInspectionFeature':
                try:
                    node = NeoInspectionFeature.nodes.get(name=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoInspectionValue':
                try:
                    node = NeoInspectionValue.nodes.get(name=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoMedServiceFeature':
                try:
                    node = NeoMedServiceFeature.nodes.get(name=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoMedServiceValue':
                try:
                    node = NeoMedServiceValue.nodes.get(name=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoTherapyFeature':
                try:
                    node = NeoTherapyFeature.nodes.get(name=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoTherapyValue':
                try:
                    node = NeoTherapyValue.nodes.get(name=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoMkb10_level_01':
                try:
                    node = NeoMkb10_level_01.nodes.get(treecode=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoMkb10_level_02':
                try:
                    node = NeoMkb10_level_02.nodes.get(treecode=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoMkb10_level_03':
                try:
                    node = NeoMkb10_level_03.nodes.get(treecode=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoMkb10_level_04':
                try:
                    node = NeoMkb10_level_04.nodes.get(treecode=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoMkb10_level_05':
                try:
                    node = NeoMkb10_level_05.nodes.get(treecode=name)
                    return node
                except DoesNotExist:
                    pass
            case 'NeoMkb10_level_06':
                try:
                    node = NeoMkb10_level_06.nodes.get(treecode=name)
                    return node
                except DoesNotExist:
                    pass
            case _:
                return {}

    def add_new_graph(
        self,
        protocol_info: Any,
        feedback: bool = False,
    ) -> None:
        # if protocol_info.get('attention_required') is True:
        #     feedback = True
        patient_id = protocol_info.get('patient_id')
        name_protocol = protocol_info.get('protocol_uuid')
        name_organ = protocol_info.get('organ')
        name_organstructure = protocol_info.get('organstructure')
        anomality = protocol_info.get('anomality')
        if anomality:
            name_anomality = anomality[0]
            anomality_attention_required = anomality[1]
        else:
            name_anomality = None
            anomality_attention_required = None
        name_featurestructures = protocol_info.get('featurestructure')
        name_anatomicalfeatures = protocol_info.get('anatomicalfeature')
        name_values = protocol_info.get('value')
        attention_required = protocol_info.get('attention_required')
        value_attention_required = protocol_info.get('value_attention_required')
        self.createpatientNode(
            name=protocol_info.get('patient_name'),
        )
        self.createprotocolNode(
            name=name_protocol,
            patient_id=patient_id,
            protocol_info=protocol_info,
        )
        self.createPatientProtocolRel(
            patient_id=patient_id,
            name_protocol=name_protocol,
            attention_required=attention_required,
        )
        if feedback:
            self.createProtocolPatientRel(
                patient_id=patient_id,
                name_protocol=name_protocol,
            )
        self.createorganNode(name=name_organ)
        self.createOrganRel(
            name_protocol=name_protocol,
            name_organ=name_organ,
            patient_id=patient_id,
            attention_required=attention_required,
            feedback=feedback,
        )
        self.createorganstructureNode(name=name_organstructure)
        self.createOrganStructureRel(
            name_organ=name_organ,
            name_organstructure=name_organstructure,
            patient_id=patient_id,
            name_protocol=name_protocol,
            feedback=feedback,
        )
        anatomicalfeatures_values = zip(name_anatomicalfeatures, name_values)
        for index, anatomicalfeature_value in enumerate(anatomicalfeatures_values):
            self.createanatomicalfeatureNode(name=anatomicalfeature_value[0])
            self.createAnatomicalFeatureRel(
                name_organ=name_organ,
                name_structure=name_organstructure,
                name_anatomicalfeature=anatomicalfeature_value[0],
                patient_id=patient_id,
                name_protocol=name_protocol,
                previous_node='NeoOrganStructure',
                feedback=feedback,
            )
            if type(anatomicalfeature_value[1]) is not int:
                # print(value_attention_required[index])
                self.createanatomicalvalueNode(
                    name=anatomicalfeature_value[1],
                    attention_required=value_attention_required[index],
                )
                self.createAnatomicalValueRel(
                    name_organ=name_organ,
                    name_organstructure=name_organstructure,
                    name_anatomicalfeature=anatomicalfeature_value[0],
                    name_anatomicalvalue=anatomicalfeature_value[1],
                    patient_id=patient_id,
                    name_protocol=name_protocol,
                    attention_required=value_attention_required[index],
                    feedback=feedback,
                )
        if name_anomality:
            self.createanomalityNode(
                name=name_anomality,
                attention_required=anomality_attention_required,
            )
            self.createAnomalityRel(
                name_organstructure=name_organstructure,
                name_anomality=name_anomality,
                patient_id=patient_id,
                name_protocol=name_protocol,
                feedback=feedback,
            )
        if name_featurestructures is not None:
            for index, name_featurestructure in enumerate(name_featurestructures):
                name_fs = name_featurestructure.get('name')[0]
                name_anatomicalfeatures = name_featurestructure.get('anatomicalfeature')
                attention_required = name_featurestructure.get('name')[1]
                self.createfeaturestructureNode(name=name_fs, attention_required=attention_required)
                self.createFeatureStructureRel(
                    name_anomality=name_anomality,
                    name_featurestructure=name_fs,
                    name_anatomicalfeature='',
                    patient_id=patient_id,
                    name_protocol=name_protocol,
                    attention_required=value_attention_required[index],
                    feedback=feedback,
                )
                for index, name_anatomicalfeature in enumerate(name_anatomicalfeatures):
                    name_value = name_featurestructure.get('value')[index]
                    attention_required = name_featurestructure.get('attention_required')[index]
                    self.createFeatureStructureAnatomicalFeatureRel(
                        name_organ=name_organ,
                        name_featurestructure=name_fs,
                        name_anatomicalfeature=name_anatomicalfeature,
                        patient_id=patient_id,
                        name_protocol=name_protocol,
                        feedback=feedback,
                    )
                    if type(name_value) is not int:
                        self.createanatomicalvalueNode(
                            name=name_value,
                            attention_required=attention_required,
                        )
                        self.createAnatomicalValueRel(
                            name_organ=name_organ,
                            name_organstructure=name_organstructure,
                            name_anatomicalfeature=name_anatomicalfeature,
                            name_anatomicalvalue=name_value,
                            patient_id=patient_id,
                            name_protocol=name_protocol,
                            attention_required=attention_required,
                            feedback=feedback,
                        )
        self.createPatientOrganRel(
            name_organ=name_organ,
            patient_id=patient_id,
            name_protocol=name_protocol,
            feedback=feedback,
        )

    def add_mkb10_graph(  # noqa: max-complexity=13
        self,
        mkb10_leveled: Any,
    ) -> None:
        mkb10_leveled_01 = mkb10_leveled[mkb10_leveled['LEVEL'] == 1]
        mkb10_leveled_02 = mkb10_leveled[mkb10_leveled['LEVEL'] == 2]
        mkb10_leveled_03 = mkb10_leveled[mkb10_leveled['LEVEL'] == 3]
        mkb10_leveled_04 = mkb10_leveled[mkb10_leveled['LEVEL'] == 4]
        mkb10_leveled_05 = mkb10_leveled[mkb10_leveled['LEVEL'] == 5]
        mkb10_leveled_06 = mkb10_leveled[mkb10_leveled['LEVEL'] == 6]
        for mkb10_level_01 in mkb10_leveled_01.iterrows():
            name = mkb10_level_01[1]['MKB_NAME']
            current_id = mkb10_level_01[1]['ID']
            parent_id = mkb10_level_01[1]['ID_PARENT']
            if np.isnan(parent_id):
                parent_id = -1
            treecode = mkb10_level_01[1]['MKB_CODE']
            level = mkb10_level_01[1]['LEVEL']
            self.create_neomkb10_level_01_node(
                name=name,
                current_id=current_id,
                parent_id=parent_id,
                treecode=treecode,
                level=level,
            )
        for mkb10_level_02 in mkb10_leveled_02.iterrows():
            name = mkb10_level_02[1]['MKB_NAME']
            current_id = mkb10_level_02[1]['ID']
            parent_id = mkb10_level_02[1]['ID_PARENT']
            if np.isnan(parent_id):
                parent_id = -1
            treecode = mkb10_level_02[1]['MKB_CODE']
            level = mkb10_level_02[1]['LEVEL']
            self.create_neomkb10_level_02_node(
                name=name,
                current_id=current_id,
                parent_id=parent_id,
                treecode=treecode,
                level=level,
            )
            treecode_parent = mkb10_leveled_01[mkb10_leveled_01.ID == parent_id]['MKB_CODE'].values[0]
            self.createMKB10_2_1_Rel(treecode_2=treecode, treecode_1=treecode_parent, status=3)
        for mkb10_level_03 in mkb10_leveled_03.iterrows():
            name = mkb10_level_03[1]['MKB_NAME']
            current_id = mkb10_level_03[1]['ID']
            parent_id = mkb10_level_03[1]['ID_PARENT']
            if np.isnan(parent_id):
                parent_id = -1
            treecode = mkb10_level_03[1]['MKB_CODE']
            level = mkb10_level_03[1]['LEVEL']
            self.create_neomkb10_level_03_node(
                name=name,
                current_id=current_id,
                parent_id=parent_id,
                treecode=treecode,
                level=level,
            )
            treecode_parent = mkb10_leveled_02[mkb10_leveled_02.ID == parent_id]['MKB_CODE'].values[0]
            self.createMKB10_3_2_Rel(treecode_3=treecode, treecode_2=treecode_parent, status=3)
        for mkb10_level_04 in mkb10_leveled_04.iterrows():
            name = mkb10_level_04[1]['MKB_NAME']
            current_id = mkb10_level_04[1]['ID']
            parent_id = mkb10_level_04[1]['ID_PARENT']
            if np.isnan(parent_id):
                parent_id = -1
            treecode = mkb10_level_04[1]['MKB_CODE']
            level = mkb10_level_04[1]['LEVEL']
            self.create_neomkb10_level_04_node(
                name=name,
                current_id=current_id,
                parent_id=parent_id,
                treecode=treecode,
                level=level,
            )
            treecode_parent = mkb10_leveled_03[mkb10_leveled_03.ID == parent_id]['MKB_CODE'].values[0]
            self.createMKB10_4_3_Rel(treecode_4=treecode, treecode_3=treecode_parent, status=3)
        for mkb10_level_05 in mkb10_leveled_05.iterrows():
            name = mkb10_level_05[1]['MKB_NAME']
            current_id = mkb10_level_05[1]['ID']
            parent_id = mkb10_level_05[1]['ID_PARENT']
            if np.isnan(parent_id):
                parent_id = -1
            treecode = mkb10_level_05[1]['MKB_CODE']
            level = mkb10_level_05[1]['LEVEL']
            self.create_neomkb10_level_05_node(
                name=name,
                current_id=current_id,
                parent_id=parent_id,
                treecode=treecode,
                level=level,
            )
            treecode_parent = mkb10_leveled_04[mkb10_leveled_04.ID == parent_id]['MKB_CODE'].values[0]
            self.createMKB10_5_4_Rel(treecode_5=treecode, treecode_4=treecode_parent, status=3)
        for mkb10_level_06 in mkb10_leveled_06.iterrows():
            name = mkb10_level_06[1]['MKB_NAME']
            current_id = mkb10_level_06[1]['ID']
            parent_id = mkb10_level_06[1]['ID_PARENT']
            if np.isnan(parent_id):
                parent_id = -1
            treecode = mkb10_level_06[1]['MKB_CODE']
            level = mkb10_level_06[1]['LEVEL']
            self.create_neomkb10_level_06_node(
                name=name,
                current_id=current_id,
                parent_id=parent_id,
                treecode=treecode,
                level=level,
            )
            treecode_parent = mkb10_leveled_05[mkb10_leveled_05.ID == parent_id]['MKB_CODE'].values[0]
            self.createMKB10_6_5_Rel(treecode_6=treecode, treecode_5=treecode_parent, status=3)

    def searchallNodes(
        self,
        node_type: Any,
    ) -> Any:
        match node_type:
            case 'NeoPatient':
                try:
                    nodes = NeoPatient.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case 'NeoProtocol':
                try:
                    nodes = NeoProtocol.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case 'NeoDisease':
                try:
                    nodes = NeoDisease.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case 'NeoPatientAnthropometryFeature':
                try:
                    nodes = NeoPatientAnthropometryFeature.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case 'NeoPatientAnthropometryValue':
                try:
                    nodes = NeoPatientAnthropometryValue.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case 'NeoPatientDemographyFeature':
                try:
                    nodes = NeoPatientDemographyFeature.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case 'NeoPatientDemographyValue':
                try:
                    nodes = NeoPatientDemographyValue.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case 'NeoOrgan':
                try:
                    nodes = NeoOrgan.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case 'NeoOrganStructure':
                try:
                    nodes = NeoOrganStructure.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case 'NeoAnomality':
                try:
                    nodes = NeoAnomality.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case 'NeoFeatureStructure':
                try:
                    nodes = NeoFeatureStructure.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case 'NeoAnatomicalFeature':
                try:
                    nodes = NeoAnatomicalFeature.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case 'NeoAnatomicalValue':
                try:
                    nodes = NeoAnatomicalValue.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case 'NeoBodyStructure':
                try:
                    nodes = NeoBodyStructure.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case 'NeoBodyFluids':
                try:
                    nodes = NeoBodyFluids.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case 'NeoSymptomFeature':
                try:
                    nodes = NeoSymptomFeature.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case 'NeoSymptomValue':
                try:
                    nodes = NeoSymptomValue.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case 'NeoInspectionFeature':
                try:
                    nodes = NeoInspectionFeature.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case 'NeoInspectionValue':
                try:
                    nodes = NeoInspectionValue.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case 'NeoMedServiceFeature':
                try:
                    nodes = NeoMedServiceFeature.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case 'NeoMedServiceValue':
                try:
                    nodes = NeoMedServiceValue.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case 'NeoTherapyFeature':
                try:
                    nodes = NeoTherapyFeature.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case 'NeoTherapyValue':
                try:
                    nodes = NeoTherapyValue.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case 'NeoMkb10_level_01':
                try:
                    nodes = NeoMkb10_level_01.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case 'NeoMkb10_level_02':
                try:
                    nodes = NeoMkb10_level_02.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case 'NeoMkb10_level_03':
                try:
                    nodes = NeoMkb10_level_03.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case 'NeoMkb10_level_04':
                try:
                    nodes = NeoMkb10_level_04.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case 'NeoMkb10_level_05':
                try:
                    nodes = NeoMkb10_level_05.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case 'NeoMkb10_level_06':
                try:
                    nodes = NeoMkb10_level_06.nodes.all()
                    return nodes
                except DoesNotExist:
                    pass
            case _:
                return {}

    def get_node_by_class_name(
        self,
        class_name: Any,
    ) -> Any:
        # Dynamic module import
        module = importlib.import_module('akcent_graph.apps.medaggregator.models')

        # # Getting a model class by name
        # model_class = getattr(module, class_name)

        # Получаем класс модели по имени
        model_cls = getattr(module, class_name)

        # if not issubclass(model_cls, 'NodeMeta):
        #     raise ValueError(f"{class_name} is not a subclass of NodeMeta")

        # Возвращаем все экземпляры данного класса
        return model_cls.nodes.all()

    def get_anamnesis_by_patient_id(
        self,
        patient_id: int,
    ) -> dict[str, dict[str, list[list[Union[str, int, uuid.UUID]]]]]:
        """
        Get all true features from protocols for one patient.
        Then cluster all these features. If there are more classes
        than the threshold value, then reclassify the existing clusters
        to the threshold value. The clusters are named by GPT.

        """
        patient = NeoPatient.nodes.first_or_none(name=patient_id)
        if not patient:
            return {}

        patient_protocols_with_attention = patient.get_all_protocols_by_attention(
            attention=[
                DataProtocolAttention.TRUE.value,
                DataProtocolAttention.TRUE_WITH_NONE.value,
            ],
        )

        grouping = ProcessingAnamnesis()
        other_anamnesis = patient.get_anamnesis_according_protocols_with_disease(
            protocols_pk=patient_protocols_with_attention,
        )
        if len(other_anamnesis) > 1:
            regroup_other_anamnesis = grouping.regroup_anamnesis_dictionary(other_anamnesis)
            if len(regroup_other_anamnesis) > config.MAXIMUM_NUMBER_OF_CLUSTERS:
                grouping = ProcessingAnamnesis(n_clusters=config.MAXIMUM_NUMBER_OF_CLUSTERS, auto_optimize=False)
                regroup_other_anamnesis = grouping.regroup_anamnesis_dictionary(
                    regroup_other_anamnesis,
                    first_iteration=False,
                )

            if regroup_other_anamnesis:
                return {'anamnesis': regroup_other_anamnesis}
        return other_anamnesis

    def get_all_class_names(
        self,
    ) -> Any:
        """This method find all class names."""
        query_all_class_names = """\
        CALL db.labels() YIELD label
        RETURN label;
        """
        class_names_response, _ = db.cypher_query(query_all_class_names)
        class_names = [class_name[0] for class_name in class_names_response]
        return class_names

    def get_parents(self, entities_of_model_class: list[Any], model_class: Any) -> dict[str, list[str]]:
        parent_attrs = []
        names_dict = {}
        for model_attr_name, model_attr_class in model_class.defined_properties().items():
            if not model_attr_name.startswith('backto_') or model_attr_name in (
                'backto_patient',
                'backto_protocol',
            ):
                continue
            if isinstance(model_attr_class, RelationshipTo):
                parent_attrs.append(model_attr_name)
        for entity in entities_of_model_class:
            parents = []
            for parent_attr in parent_attrs:
                try:
                    parents.extend([entry.name for entry in getattr(entity, parent_attr).all()])
                except CardinalityViolation:
                    continue
            names_dict = {entity.name: list(set(parents)) for entity in entities_of_model_class}
        return names_dict

    def get_all_entities_by_class_names(
        self,
        class_names: Any = None,
        module_name: str = 'akcent_graph.apps.medaggregator.models',
        exclude: Optional[List[str]] = None,
        with_parents: bool = False,
    ) -> Any:
        """This method get entities by class names.
        class_names: list of class names to obtain all entities of each class\n
        module_name: place where models are located\n
        exclude: list of class names to exclude from class_names
        If class_names is empty, return all entities of all class names, excluded classes in exclude list.
        """
        if not exclude:
            exclude = [
                'NeoPatient',
                'NeoProtocol',
                'NeoMkb10_level_01',
                'NeoMkb10_level_02',
                'NeoMkb10_level_03',
                'NeoMkb10_level_04',
                'NeoMkb10_level_05',
                'NeoMkb10_level_06',
            ]
        # Dynamic module import
        if class_names is None:
            class_names = self.get_all_class_names()
        class_names = list(set(class_names) - set(exclude))
        module = importlib.import_module(module_name)
        entities: dict[str, Any] = {}
        if not class_names:
            return entities

        if class_names == [('NeoDisease', 'treecode')]:
            treecode_diseases = []
            treecode_diseases_dict = {}
            model_class_disease = getattr(module, class_names[0][0])
            entities_of_disease = model_class_disease.nodes.all()
            for entity_disease in entities_of_disease:
                if entity_disease.treecode:
                    treecode_diseases.append(entity_disease.treecode)
            treecode_diseases_dict[class_names[0][0]] = treecode_diseases
            return treecode_diseases_dict

        for class_name in class_names:
            model_class = getattr(module, class_name)
            entities_of_model_class = model_class.nodes.all()
            if with_parents:
                entities[class_name] = self.get_parents(entities_of_model_class, model_class)
            else:
                entities[class_name] = [entity.name for entity in entities_of_model_class]
        return entities

    def get_extract_by_patient_id(
        self,
        patient_id: Any,
        is_extract: bool = True,
    ) -> Any:
        """This method get from graphdb extract of patient with patient_id.
        patient_extract includes diseases, short anamnesis, therapy.
        patient_id: patient_id of patient\n
        element[0]: name of disease\n
        element[1]: treecode of disease (if needed)\n
        element[2]: short anamnesis and therapy\n
        extract: dictionary where keys are diseases and values are extract for disease
        """
        patient_extract = {}
        diseases = {}  # type: ignore
        # Create patient with patient_id
        patient = NeoPatient.nodes.first_or_none(name=patient_id)
        if patient:
            patient_diseases = patient.get_all_diseases_according_protocols()
        else:
            return {}
        for element in patient_diseases:
            if not diseases.get(element[0]):
                diseases[element[0]] = [element[2]]
            elif element[2] not in diseases[element[0]]:
                value = diseases[element[0]]
                value.append(element[2])
                diseases[element[0]] = value
        for disease, protocols_pk in diseases.items():
            if disease:
                patient_extract[disease] = patient.get_anamnesis_according_protocols_with_disease(
                    protocols_pk=protocols_pk,
                )
        gpt = GPT()
        extract = {}
        extract_sample = (
            '6. Полный диагноз (основное заболевание, сопутствующее осложнение).',
            '7. Краткий анамнез, диагностические исследования, течение болезни, проведенное лечение, '
            'состояние при направлении, при выписке.',
            '8. Лечебные и трудовые рекомендации:',
        )
        for disease, anamnesis in patient_extract.items():
            system_role, user_role = get_prompt_of_description_extract(
                anamnesis=str(anamnesis),
                disease=str(disease),
                extract_sample=str(extract_sample),
            )
            answer_of_gpt = gpt.make_request(system_prompt=system_role, prompt=user_role)
            extract[disease] = answer_of_gpt
        return extract

    def merge_nodes_and_relationships_by_neuro(
        self,
        start_node_label: str,
        start_node_name: str,
        end_node_label: str,
        end_node_name: str,
        chain: str,
        protocol_pk: int,
        patient_id: int,
        value: str = '',
        relationship_type: str = DataRelationshipNamingByNeuro.NEURO_NAME.value,
        created_by_neuro: int = DataCreatedByNeuro.TRUE.value,
        attention: int = DataImportanceFeature.NONE_IMPORTANCE.value,
    ) -> Any:
        query_template = """\
        MERGE (child:`{label_child}` {{name: $name_child}})
        MERGE (parent:`{label_parent}` {{name: $name_parent}})
        MERGE (child)-[:`{relationship}` {{
            chain: $chain,
            value: $value,
            protocol_pk: $protocol_pk,
            patient_id: $patient_id,
            created_by_neuro: $created_by_neuro,
            attention: $attention}}]->(parent)
        """
        query_created_by_neuro = query_template.format(
            label_child=start_node_label,
            label_parent=end_node_label,
            relationship=relationship_type,
            chain=chain,
            created_by_neuro=created_by_neuro,
            attention=attention,
        )
        params = {
            'name_child': start_node_name,
            'name_parent': end_node_name,
            'chain': chain,
            'value': value,
            'protocol_pk': protocol_pk,
            'patient_id': patient_id,
            'created_by_neuro': created_by_neuro,
            'attention': attention,
        }
        if not self.is_test:
            find_paths, _ = db.cypher_query(query_created_by_neuro, params)
            return find_paths, _
        else:
            return query_created_by_neuro

    def match_parent_not_found_key_value_by_neuro(
        self,
        start_node_label: str,
        start_node_name: str,
        end_node_label: str,
        end_node_name: str,
        chain: str,
        protocol_pk: int,
        patient_id: int,
        relationship_type: str = DataRelationshipNamingByNeuro.NEURO_NAME.value,
        created_by_neuro: int = DataCreatedByNeuro.TRUE.value,
        parent_not_found: int = DataParentNotFound.FOUND_PARENT.value,
    ) -> Any:
        query_template = """\
        MATCH (start:`{label_start}` {{name: $name_start}})<-[r]-(end:`{label_end}` {{name: $name_end}})
        WHERE r.patient_id={patient_id} and r.protocol_pk={protocol_pk}
        SET r.parent_not_found={parent_not_found}
        SET r.chain='{chain}'
        SET r.created_by_neuro={created_by_neuro}
        """
        query_created_by_neuro = query_template.format(
            label_start=start_node_label,
            label_end=end_node_label,
            relationship=relationship_type,
            patient_id=patient_id,
            protocol_pk=protocol_pk,
            parent_not_found=parent_not_found,
            chain=chain,
            created_by_neuro=created_by_neuro,
        )
        params = {
            'name_start': start_node_name,
            'name_end': end_node_name,
        }
        if not self.is_test:
            find_paths, _ = db.cypher_query(query_created_by_neuro, params)
            return find_paths, _
        else:
            return query_created_by_neuro

    def delete_entity(
        self,
        entity_name: str,
        entity_class: str,
        query_delete_template: str = """\
        MATCH (n:`{current_class_name}` {{name: $name}})
        WHERE NOT (n)--()
        DELETE n;
        """,
    ) -> str:
        query_delete = query_delete_template.format(
            current_class_name=entity_class,
        )
        params = {
            'name': entity_name,
        }
        if not self.is_test:
            db.cypher_query(query_delete, params)
            return f'Delete entity {entity_name} of {entity_class} class without relations.'
        else:
            return query_delete

    def detach_delete_entity(
        self,
        entity_name: str,
        entity_class: str,
        query_delete_template: str = """\
        MATCH (n:`{current_class_name}` {{name: $name}})
        DETACH DELETE n;
        """,
    ) -> str:
        query_delete = query_delete_template.format(
            current_class_name=entity_class,
        )
        params = {
            'name': entity_name,
        }
        if not self.is_test:
            db.cypher_query(query_delete, params)
            return f'Delete entity {entity_name} of {entity_class} class on detach case.'
        else:
            return query_delete

    def detach_delete_entity_by_id(
        self,
        entity_id: str,
        query_delete_by_id_template: str = """\
        MATCH (entity)
        WHERE ID(entity) = {id}
        DETACH DELETE entity;
        """,
    ) -> str:
        query_delete_by_id = query_delete_by_id_template.format(
            id=entity_id,
        )
        if not self.is_test:
            db.cypher_query(query_delete_by_id)
            return f'Delete entity with id = {entity_id}!'
        else:
            return query_delete_by_id

    def count_relations_by_id(
        self,
        entity_id: int = -1,
        query_count_relations_template: str = """\
        MATCH (entity)
        WHERE ID(entity) = {id}
        OPTIONAL MATCH ()-[relationship_in]->(entity)
        WITH entity, count(relationship_in) AS incoming_relationships
        OPTIONAL MATCH (entity)-[relationship_out]->()
        RETURN ID(entity) AS entity_id, incoming_relationships + count(relationship_out) AS total_connections, incoming_relationships, count(relationship_out) AS outcoming_relationships;
        """,
    ) -> Any:
        query_count_relations = query_count_relations_template.format(
            id=entity_id,
        )
        if not self.is_test:
            find_paths, _ = db.cypher_query(query_count_relations)
            return find_paths, _
        else:
            return query_count_relations

    def return_id_by_name_and_class_name(
        self,
        entity_name: str,
        entity_class: str,
        query_delete_template: str = """\
        MATCH (n:`{current_class_name}` {{name: $name}})
        RETURN ID(n);
        """,
    ) -> List[List[int | str]]:
        query_delete = query_delete_template.format(
            current_class_name=entity_class,
        )
        params = {
            'name': entity_name,
        }
        if not self.is_test:
            node_id, _ = db.cypher_query(query_delete, params)
            return node_id
        else:
            return [[query_delete]]

    def create_relation_by_info(
        self,
        relation_info: tuple[str | int | Any, str | int | Any, Any, Any],
        query: str = DataCypherQueriesNeoSpider.TRANSFER_RELATIONSHIP.value,
    ) -> None:
        start_id = relation_info[0]
        end_id = relation_info[1]
        relationship_type = relation_info[2]
        relationship_properties = convert_dict_to_special_string(relation_info[3])
        query_create_relation = query.format(
            relationship_type=relationship_type,
            relationship_properties=relationship_properties,
            start_id=start_id,
            end_id=end_id,
        )
        if not self.is_test:
            db.cypher_query(query_create_relation)
            return None
        else:
            return None

    def rename_label(
        self,
        current_id: str,
        old_label: str,
        new_label: str,
        query: str = DataCypherQueriesNeoSpider.RENAME_LABEL.value,
    ) -> str:
        query_rename_label = query.format(
            old_label=old_label,
            new_label=new_label,
            current_id=current_id,
        )
        if not self.is_test:
            db.cypher_query(query_rename_label)
            return f'Rename label {old_label} to {new_label}!'
        else:
            return query_rename_label
