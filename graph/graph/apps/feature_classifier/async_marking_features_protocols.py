# pylint: disable=duplicate-code

import logging
from typing import Optional, Union

from asgiref.sync import sync_to_async
from constance import config
from django.conf import settings
from neomodel import db
from pandas import DataFrame, Series

from akcent_graph.apps.feature_classifier.processing_medical_records import ProcessingMedicalRecords
from akcent_graph.apps.feature_classifier.queries_db import QueryMarkingFeatures
from akcent_graph.apps.medaggregator.helpers import (
    SCORE_FOR_ERRORS,
    DataAutoImportance,
    DataImportanceFeature,
    DataProtocolAttention,
)
from akcent_graph.apps.medaggregator.models import NeoProtocol
from akcent_graph.utils.timing import timing

logger = logging.getLogger(__name__)


class AsyncMarkingProtocol:
    @timing
    def __init__(
        self,
        single_features_pkl: bool = True,
    ) -> None:
        if single_features_pkl:
            self.recorder = ProcessingMedicalRecords(
                data_path_ann=settings.ICD_SYMPTOM_DATA_ANN,
                size_ann=config.ICD_SYMPTOM_SIZE,
                metric_ann=config.ICD_SYMPTOM_METRIC,
            )
        else:
            self.recorder = ProcessingMedicalRecords(
                settings.MERGE_ICD_SYMPTOM_DATA,
            )
        self.relation_attention_marker = {
            True: DataImportanceFeature.TRUE_IMPORTANCE.value,
            False: DataImportanceFeature.FALSE_IMPORTANCE.value,
            None: DataImportanceFeature.NONE_IMPORTANCE.value,
        }

    @timing
    async def get_connection_between_nodes(
        self,
        feature: Series,
        parent: Series,
        protocol_id: int,
        chain: str,
        is_error: bool,
        logging_from_marked: str,
    ) -> tuple[bool, bool, str]:
        """
        The function checks whether there is a connection between two nodes
        of a certain puncture in the graph database if there is a certain
        value in the chain on the connection.

        """
        current_query: Union[str, bool] = (
            QueryMarkingFeatures.IS_CONNECTION_BETWEEN_NODES.value.replace(
                '{class_daughter}',
                feature['class_parent_node'],
            )
            .replace(
                '{class_parent}',
                parent['class_parent_node'],
            )
            .replace(
                '{protocol_pk}',
                str(protocol_id),
            )
        )

        current_query, is_error, logging_from_marked = await self.replace_variable_with_quotes(
            current_query,
            feature['name_parent_node'],
            '{name_daughter}',
            is_error,
            logging_from_marked,
        )
        if current_query is True:
            current_logging = f'Error in getting of connection between nodes of protocol: {protocol_id}'
            logger.error(current_logging)
            is_error = True
            logging_from_marked += f'\n\n{current_logging}'
            return False, is_error, logging_from_marked
        current_query, is_error, logging_from_marked = await self.replace_variable_with_quotes(
            current_query,
            parent['name_parent_node'],
            '{name_parent}',
            is_error,
            logging_from_marked,
        )
        if current_query is True:
            current_logging = f'Error in getting of connection between nodes of protocol: {protocol_id}'
            logger.error(current_logging)
            is_error = True
            logging_from_marked += f'\n\n{current_logging}'
            return False, is_error, logging_from_marked
        current_query, is_error, logging_from_marked = await self.replace_variable_with_quotes(
            current_query,
            chain,
            '{chain}',
            is_error,
            logging_from_marked,
        )
        if current_query is True:
            current_logging = f'Error in getting of connection between nodes of protocol: {protocol_id}'
            logger.error(current_logging)
            is_error = True
            logging_from_marked += f'\n\n{current_logging}'
            return False, is_error, logging_from_marked
        current_query, is_error, logging_from_marked = await self.replace_variable_with_quotes(
            current_query,
            feature['value_parent_node'],
            '{value_daughter}',
            is_error,
            logging_from_marked,
        )
        if current_query is True:
            current_logging = f'Error in getting of connection between nodes of protocol: {protocol_id}'
            logger.error(current_logging)
            is_error = True
            logging_from_marked += f'\n\n{current_logging}'
            return False, is_error, logging_from_marked

        data, columns = db.cypher_query(current_query)  # pylint: disable=unused-variable
        if data:
            return True, is_error, logging_from_marked
        return False, is_error, logging_from_marked

    @timing
    async def filter_last_relations(
        self,
        table_query: DataFrame,
        protocol_id: int,
        is_error: bool,
        logging_from_marked: str,
    ) -> tuple[DataFrame, DataFrame, bool, str]:
        """
        Get the last relation in a chain of nodes.
        Return: first table is last relations,
        second table is transitional relations.
        The search for the latest feature is carried out by chain.

        """
        parents_indexes = set()
        for index, feature in table_query.iterrows():
            if settings.CHAIN_SEPARATOR in feature['chain_parent_node']:
                search_chain = self.recorder.trim_string(feature['chain_parent_node'], settings.CHAIN_SEPARATOR)
                parent_table = table_query.loc[table_query['chain_parent_node'] == search_chain]
                for index, row in parent_table.iterrows():
                    presence_of_path, is_error, logging_from_marked = await self.get_connection_between_nodes(
                        feature,
                        row,
                        protocol_id,
                        search_chain,
                        is_error,
                        logging_from_marked,
                    )
                    if presence_of_path:
                        parents_indexes.add(index)

        parents_indexes.difference_update(
            table_query[
                table_query['value_parent_node'].apply(  # pylint: disable=singleton-comparison
                    self.recorder.contains_alphanumeric,
                )
                == True  # noqa E712
            ].index.to_list(),
        )

        return (
            table_query[~table_query.index.isin(parents_indexes)],
            table_query[table_query.index.isin(parents_indexes)],
            is_error,
            logging_from_marked,
        )

    @timing
    async def update_protocol_attention(
        self,
        markers_in_protocol: set[None | bool],
        protocol: NeoProtocol,
    ) -> None:
        if True in markers_in_protocol and None in markers_in_protocol:
            protocol.attention_required = DataProtocolAttention.TRUE_WITH_NONE.value
        elif True in markers_in_protocol:
            protocol.attention_required = DataProtocolAttention.TRUE.value
        elif None in markers_in_protocol:
            protocol.attention_required = DataProtocolAttention.NONE.value
        else:
            protocol.attention_required = DataProtocolAttention.FALSE.value
        await sync_to_async(protocol.save)()

    async def marking_new_protocol(
        self,
        protocol: NeoProtocol,
    ) -> tuple[set[Union[None, bool]], bool, str]:
        protocol_id = protocol.name
        patient_id = protocol.patient_id
        is_error = False
        logging_from_marked = ''

        current_query: Union[str, bool] = QueryMarkingFeatures.FIRST_MARKING_QUERY.value.replace(
            '{protocol.name}',
            str(protocol_id),
        ).replace(
            '{protocol.patient}',
            str(patient_id),
        )
        data, columns = db.cypher_query(current_query)
        table_query = DataFrame(data, columns=columns)
        table_for_marking, table_false_marking, is_error, logging_from_marked = await self.filter_last_relations(
            table_query,
            protocol_id,
            is_error,
            logging_from_marked,
        )

        for index, feature in table_false_marking.iterrows():  # pylint: disable=unused-variable
            is_error, logging_from_marked = await self.update_attention_on_edge_bd(
                False,
                feature.name_parent_node,
                feature.class_parent_node,
                feature.chain_parent_node,
                feature.value_parent_node,
                protocol_id,
                patient_id,
                is_error,
                logging_from_marked,
                query=QueryMarkingFeatures.CHANGE_ATTENTION_RELATION.value,
                with_score=False,
            )

        in_protocol_attention = set()

        for index, feature in table_for_marking.iterrows():
            chain = feature.chain_parent_node.split(settings.CHAIN_SEPARATOR)

            marker, score = await self.marking_one_feature(
                chain,
                feature.class_parent_node,
                feature.value_parent_node,
            )

            in_protocol_attention.add(marker)
            is_error, logging_from_marked = await self.update_attention_on_edge_bd(
                marker,
                feature.name_parent_node,
                feature.class_parent_node,
                feature.chain_parent_node,
                feature.value_parent_node,
                protocol_id,
                patient_id,
                is_error,
                logging_from_marked,
                score,
            )
        await self.update_protocol_attention(
            in_protocol_attention,
            protocol,
        )
        return in_protocol_attention, is_error, logging_from_marked

    @timing
    async def get_score_from_annoy_score(
        self,
        annoy_score: dict[str, float],
    ) -> Optional[float]:
        scores = list(annoy_score.values())
        if scores:
            return scores[0]
        return SCORE_FOR_ERRORS

    @timing
    async def marking_one_feature(
        self,
        chain: list[str],
        parent_class: str,
        feature_value: str,
    ) -> tuple[Optional[bool], Optional[float]]:
        if len(chain) > 1:
            name = chain[0]
            value = f"{', '.join(chain[1:])} {str(feature_value).replace('[', '').replace(']', '')}"
        else:
            name = ''
            value = chain[0]
        is_value_for_feature = self.recorder.contains_alphanumeric(feature_value)

        if (parent_class in DataAutoImportance.NODE_FALSE_IMPORTANCE.value) or (
            parent_class in DataAutoImportance.NODE_IF_VALUE_NOT_FALSE.value and not is_value_for_feature
        ):
            marker = False
            score = None
        elif parent_class in DataAutoImportance.NODE_TRUE_IMPORTANCE.value:
            marker = True
            score = None
        elif (
            len(chain) == 1 and parent_class in DataAutoImportance.FALSE_SINGLE_NODE.value and not is_value_for_feature
        ):
            marker = False
            score = None
        else:
            marker, annoy_score = await sync_to_async(self.recorder.determining_feature_importance)(name, value)
            score = await self.get_score_from_annoy_score(annoy_score)
        return marker, score

    @timing
    async def replace_variable_with_quotes(
        self,
        current_query: str,
        name_variable: str,
        sample: str,
        is_error: bool,
        logging_from_marked: str,
    ) -> tuple[Union[str, bool], bool, str]:
        if "'" in name_variable and '"' in name_variable:
            current_logging = f'Cypher query contains single and double quotes: {name_variable}'
            logger.error(current_logging)
            is_error = True
            logging_from_marked += f'\n\n{current_logging}'
            return True, is_error, logging_from_marked
        if "'" in name_variable:
            current_query = current_query.replace(
                sample,
                f'"{name_variable}"',
            )
        else:
            current_query = current_query.replace(
                sample,
                f"'{name_variable}'",
            )
        return current_query, is_error, logging_from_marked

    @timing
    async def update_attention_on_edge_bd(
        self,
        marker: Optional[bool],
        name_feature: str,
        class_feature: str,
        chain_feature: str,
        feature_value: str,
        protocol_id: int,
        patient_id: int,
        is_error: bool,
        logging_from_marked: str,
        score: Optional[float] = None,
        query: str = QueryMarkingFeatures.CHANGE_ATTENTION_SCORE_RELATION.value,
        with_score: bool = True,
    ) -> tuple[bool, str]:
        marker_for_db = self.relation_attention_marker[marker]

        current_query: Union[str, bool] = (
            query.replace(
                '{class_feature}',
                class_feature,
            )
            .replace(
                '{patient_id}',
                str(patient_id),
            )
            .replace(
                '{protocol_pk}',
                str(protocol_id),
            )
            .replace(
                '{new_attention}',
                str(marker_for_db),
            )
        )

        current_query, is_error, logging_from_marked = await self.replace_variable_with_quotes(
            current_query,
            name_feature,
            '{name_feature}',
            is_error,
            logging_from_marked,
        )
        if current_query is True:
            current_logging = f'Error in save attention on edge of protocol: {protocol_id}'
            logger.error(current_logging)
            is_error = True
            logging_from_marked += f'\n\n{current_logging}'
            return is_error, logging_from_marked
        current_query, is_error, logging_from_marked = await self.replace_variable_with_quotes(
            current_query,
            chain_feature,
            '{feature_chain}',
            is_error,
            logging_from_marked,
        )
        if current_query is True:
            current_logging = f'Error in save attention on edge of protocol: {protocol_id}'
            logger.error(current_logging)
            is_error = True
            logging_from_marked += f'\n\n{current_logging}'
            return is_error, logging_from_marked
        current_query, is_error, logging_from_marked = await self.replace_variable_with_quotes(
            current_query,
            feature_value,
            '{feature_value}',
            is_error,
            logging_from_marked,
        )
        if current_query is True:
            current_logging = f'Error in save attention on edge of protocol: {protocol_id}'
            logger.error(current_logging)
            is_error = True
            logging_from_marked += f'\n\n{current_logging}'
            return is_error, logging_from_marked

        if with_score and isinstance(current_query, str):
            if score:
                score_for_db = str(score)
            else:
                score_for_db = 'NULL'
            current_query = current_query.replace(
                '{new_score}',
                score_for_db,
            )

        db.cypher_query(current_query)
        return is_error, logging_from_marked
