# pylint: disable=duplicate-code

import logging
from typing import Optional, Union

from constance import config
from django.conf import settings
from neomodel import db
from pandas import DataFrame, Series, concat

from akcent_graph.apps.feature_classifier.processing_medical_records import ProcessingMedicalRecords
from akcent_graph.apps.feature_classifier.queries_db import QueryMarkingFeatures
from akcent_graph.apps.medaggregator.helpers import (
    SCORE_FOR_ERRORS,
    DataAutoImportance,
    DataImportanceFeature,
    DataProtocolAttention,
)
from akcent_graph.apps.medaggregator.models import NeoProtocol, Protocol
from akcent_graph.utils.timing import timing

logger = logging.getLogger(__name__)


class MarkingProtocol:
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
    def get_connection_between_nodes(
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

        current_query, is_error, logging_from_marked = self.replace_variable_with_quotes(
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
        current_query, is_error, logging_from_marked = self.replace_variable_with_quotes(
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
        current_query, is_error, logging_from_marked = self.replace_variable_with_quotes(
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
        current_query, is_error, logging_from_marked = self.replace_variable_with_quotes(
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
    def filter_last_relations(
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
                    presence_of_path, is_error, logging_from_marked = self.get_connection_between_nodes(
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
    def get_score_from_annoy_score(
        self,
        annoy_score: dict[str, float],
    ) -> Optional[float]:
        scores = list(annoy_score.values())
        if scores:
            return scores[0]
        return SCORE_FOR_ERRORS

    @timing
    def marking_one_feature(
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
            (
                marker,
                annoy_score,
            ) = self.recorder.determining_feature_importance(
                name,
                value,
            )
            score = self.get_score_from_annoy_score(annoy_score)
        return marker, score

    @timing
    def replace_variable_with_quotes(
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
    def update_attention_on_edge_bd(
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

        current_query, is_error, logging_from_marked = self.replace_variable_with_quotes(
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
        current_query, is_error, logging_from_marked = self.replace_variable_with_quotes(
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
        current_query, is_error, logging_from_marked = self.replace_variable_with_quotes(
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

    @timing
    def update_protocol_attention(
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
        protocol.save()

    @timing
    def marking_new_protocol(
        self,
        protocol: NeoProtocol,
    ) -> tuple[set[Union[None, bool]], bool, str]:
        protocol_id = protocol.name
        patient_id = protocol.patient_id
        is_error = False
        logging_from_marked = ''

        current_query = QueryMarkingFeatures.FIRST_MARKING_QUERY.value.replace(
            '{protocol.name}',
            str(protocol_id),
        ).replace(
            '{protocol.patient}',
            str(patient_id),
        )
        data, columns = db.cypher_query(current_query)
        table_query = DataFrame(data, columns=columns)
        table_for_marking, table_false_marking, is_error, logging_from_marked = self.filter_last_relations(
            table_query,
            protocol_id,
            is_error,
            logging_from_marked,
        )

        for index, feature in table_false_marking.iterrows():  # pylint: disable=unused-variable
            is_error, logging_from_marked = self.update_attention_on_edge_bd(
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

            marker, score = self.marking_one_feature(
                chain,
                feature.class_parent_node,
                feature.value_parent_node,
            )

            in_protocol_attention.add(marker)
            is_error, logging_from_marked = self.update_attention_on_edge_bd(
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
        self.update_protocol_attention(
            in_protocol_attention,
            protocol,
        )
        return in_protocol_attention, is_error, logging_from_marked

    @timing
    def search_additional_feature(
        self,
        current_feature: Series,
        true_table: DataFrame,
    ) -> tuple[DataFrame, list[int]]:
        hierarchy_slice_indexes = []

        hierarchy_true_date = true_table.loc[
            true_table['chain_parent_node'].str.contains(  # pylint: disable=singleton-comparison
                f'{current_feature.chain_parent_node}{settings.CHAIN_SEPARATOR}',
                regex=False,
            )
            == True  # noqa E712
        ]
        if not hierarchy_true_date.empty:
            hierarchy_slice_indexes.append(hierarchy_true_date.shape[0])

        tree_hierarchy_slice = len(current_feature.split_chain) - 1
        if tree_hierarchy_slice > 0:
            while tree_hierarchy_slice != 0:
                search_chain = settings.CHAIN_SEPARATOR.join(current_feature.split_chain[:tree_hierarchy_slice])
                parent_true_date = true_table.loc[
                    true_table['chain_parent_node'].str.contains(  # pylint: disable=singleton-comparison
                        search_chain,
                        regex=False,
                    )
                    == True  # noqa E712
                ]

                if not parent_true_date.empty:
                    hierarchy_true_date = concat(
                        [hierarchy_true_date, parent_true_date],
                        axis=0,
                    ).drop_duplicates(
                        subset=[
                            'name_parent_node',
                            'value_parent_node',
                            'chain_parent_node',
                            'attention',
                            'score',
                            'protocol',
                        ],
                        keep='first',
                    )
                    hierarchy_slice_indexes.append(hierarchy_true_date.shape[0])

                tree_hierarchy_slice -= 1

        if not hierarchy_true_date.empty:
            logger.info(
                'The top of the hierarchy for additional marking has been reached',
            )
        return hierarchy_true_date, hierarchy_slice_indexes

    @timing
    def additional_update_attention(
        self,
        protocols: list[int],
        patient_id: int,
        is_error: bool,
        logging_from_marked: str,
    ) -> tuple[bool, str]:
        for protocol_pk in protocols:
            current_query = QueryMarkingFeatures.UNIQUE_ATTENTION_IN_PROTOCOL.value.replace(
                '{protocol_pk}',
                str(protocol_pk),
            ).replace(
                '{patient_id}',
                str(patient_id),
            )
            data, columns = db.cypher_query(current_query)  # pylint: disable=unused-variable

            in_protocol_attention = set()
            for attention_in_list in data:
                in_protocol_attention.add(attention_in_list[0])

            try:
                neo_protocol = NeoProtocol.nodes.filter(  # pylint: disable=no-member
                    patient_id=patient_id,
                    name=protocol_pk,
                ).first()
            except NeoProtocol.DoesNotExist:  # pylint: disable=no-member
                current_logging = f'NeoProtocol does not exist with name: {protocol_pk} and patient_id: {patient_id}'
                logger.error(current_logging)
                is_error = True
                logging_from_marked += f'\n\n{current_logging}'
                return is_error, logging_from_marked
            postgre_protocol = Protocol.objects.get(pk=protocol_pk)
            if (
                DataImportanceFeature.TRUE_IMPORTANCE.value in in_protocol_attention
                and DataImportanceFeature.NONE_IMPORTANCE.value in in_protocol_attention
            ):
                neo_protocol.attention_required = DataProtocolAttention.TRUE_WITH_NONE.value
                postgre_protocol.unmarked_features_left = True
                postgre_protocol.attentions_changed = True
            elif DataImportanceFeature.TRUE_IMPORTANCE.value in in_protocol_attention:
                neo_protocol.attention_required = DataProtocolAttention.TRUE.value
                postgre_protocol.attentions_changed = True
                postgre_protocol.unmarked_features_left = False
            elif DataImportanceFeature.NONE_IMPORTANCE.value in in_protocol_attention:
                neo_protocol.attention_required = DataProtocolAttention.NONE.value
                postgre_protocol.unmarked_features_left = True
            else:
                neo_protocol.attention_required = DataProtocolAttention.FALSE.value
                postgre_protocol.unmarked_features_left = False
            neo_protocol.save()
            postgre_protocol.save()
        return is_error, logging_from_marked

    @timing
    def get_disease_for_protocols(
        self,
        protocols: list[int],
        patient_id: int,
    ) -> Optional[dict[int, list[str]]]:
        disease_query = QueryMarkingFeatures.DISEASE_OF_PROTOCOL.value.replace(
            '{protocol_ids}',
            str(protocols),
        ).replace(
            '{patient_id}',
            str(patient_id),
        )
        diseases_data, disease_columns = db.cypher_query(disease_query)  # pylint: disable=unused-variable

        dict_diseases: dict[int, list[str]] = {}
        for disease, protocol in diseases_data:
            if dict_diseases.get(protocol):
                diseases = dict_diseases[protocol] + [disease]
                dict_diseases[protocol] = diseases
            else:
                dict_diseases[protocol] = [disease]
        return dict_diseases

    @timing
    def contains_chain_in_one_protocol(
        self,
        feature: Series,
        patient_id: int,
        is_error: bool,
        logging_from_marked: str,
    ) -> tuple[bool, bool, str]:
        """
        Check if the node is the last in the chain by chain:
        request nodes containing the feature chain;
        check the connections of the received nodes with the feature.

        """
        current_query: Union[str, bool] = QueryMarkingFeatures.CONTAINS_CHAIN_ONE_PROTOCOL.value.replace(
            '{protocol_pk}',
            str(feature.protocol),
        )

        current_query, is_error, logging_from_marked = self.replace_variable_with_quotes(
            current_query,
            feature.chain_parent_node,
            '{chain}',
            is_error,
            logging_from_marked,
        )
        if current_query is True:
            current_logging = f'Error in the content of the chain in the patient: {patient_id}'
            logger.error(current_logging)
            is_error = True
            logging_from_marked += f'\n\n{current_logging}'
            return False, is_error, logging_from_marked
        current_query, is_error, logging_from_marked = self.replace_variable_with_quotes(
            current_query,
            feature.name_parent_node,
            '{name_feature}',
            is_error,
            logging_from_marked,
        )
        if current_query is True:
            current_logging = f'Error in the content of the chain in the patient: {patient_id}'
            logger.error(current_logging)
            is_error = True
            logging_from_marked += f'\n\n{current_logging}'
            return False, is_error, logging_from_marked
        current_query, is_error, logging_from_marked = self.replace_variable_with_quotes(
            current_query,
            feature.value_parent_node,
            '{value}',
            is_error,
            logging_from_marked,
        )
        if current_query is True:
            current_logging = f'Error in the content of the chain in the patient: {patient_id}'
            logger.error(current_logging)
            is_error = True
            logging_from_marked += f'\n\n{current_logging}'
            return False, is_error, logging_from_marked

        data, columns = db.cypher_query(current_query)
        table_chain_nodes = DataFrame(data, columns=columns)

        for index, chain_feature in table_chain_nodes.iterrows():  # pylint: disable=unused-variable
            presence_of_path, is_error, logging_from_marked = self.get_connection_between_nodes(
                chain_feature,
                feature,
                feature.protocol,
                chain_feature.chain,
                is_error,
                logging_from_marked,
            )
            if presence_of_path:
                return presence_of_path, is_error, logging_from_marked
        return False, is_error, logging_from_marked

    @timing
    def get_maker_by_diagnosis(
        self,
        feature_name: str,
        feature_value: str,
        feature_diseases: list[str],
        true_table: DataFrame,
        is_error: bool,
        logging_from_marked: str,
    ) -> tuple[Optional[bool], bool, str]:
        if feature_diseases:
            slice_diseases_table = true_table[~true_table.diseases.isnull()]
            slice_diseases_table['is_deseases'] = slice_diseases_table['diseases'].apply(
                lambda diseases: any(disease in feature_diseases for disease in diseases),
            )
            slice_diseases_table = slice_diseases_table.loc[
                slice_diseases_table.is_deseases == True  # pylint: disable=singleton-comparison  # noqa E712
            ]

            if not slice_diseases_table.empty:
                try:
                    embedding_features = self.recorder.get_iteration_sum(
                        slice_diseases_table,
                    )
                except IndexError as error:
                    current_logging = f'No embedding received for additional feature. Error: {error}'
                    logger.warning(current_logging)
                    is_error = True
                    logging_from_marked += f'\n\n{current_logging}'
                    return None, is_error, logging_from_marked

                logger.info(
                    'Further score by the sum according to the diagnosis.',
                )
                marker = self.recorder.determining_importance_with_additional_feature(
                    feature_name,
                    feature_value,
                    embedding_features,
                    slice_diseases_table.shape[0],
                )
                logger.info(
                    'Ending at the sum according to the diagnosis.',
                )
                return marker, is_error, logging_from_marked

        return None, is_error, logging_from_marked

    @timing
    def get_markers_for_rated_none_feature(
        self,
        feature_row: Series,
        true_table: DataFrame,
        patient_id: int,
        markers: set[Union[None, bool]],
        is_error: bool,
        logging_from_marked: str,
    ) -> tuple[bool, str]:
        """
        It is checked whether the feature is the last in the chain in its protocol, if it belongs,
        then False is adding in markers. Otherwise, we get a paraphrase of the feature chain
        description and its value (if any) from GPT. Then we take all True features from the
        neighboring branch by parent, if there are none, we go up to the parent until we reach
        the end of the tree. We add up all True features, see what diseases they belong to. Then
        we add the None feature, look at the assessment by diseases. We compare whether there is
        a convergence to some disease. Based on the top diseases, we fill in markers in positive,
        negative or insignificant convergence .

        If at the stage of obtaining True features from the tree, not a single True feature was
        found, then we look for all trees with the same diagnosis as the diagnosis of the
        protocol, where the None feature is located. Also, all vectors are added up and
        convergence by diseases is looked for, before and after adding the None feature.

        Throughout the pipeline, we collect all errors that occurred in the code. We
        return the presence of errors and their text from the function.

        """
        is_containing, is_error, logging_from_marked = self.contains_chain_in_one_protocol(
            feature_row,
            patient_id,
            is_error,
            logging_from_marked,
        )
        if is_containing:
            markers.add(False)
        else:
            current_feature_name, current_feature_value = self.recorder.get_name_value_from_row_feature(
                feature_row,
            )

            hierarchy_true_date, hierarchy_slice_indexes = self.search_additional_feature(
                feature_row,
                true_table,
            )

            for iteration in hierarchy_slice_indexes:
                slice_hierarchy_true_date = hierarchy_true_date[:iteration]
                if not slice_hierarchy_true_date.empty:
                    try:
                        embedding_features = self.recorder.get_iteration_sum(
                            slice_hierarchy_true_date,
                        )
                    except TypeError as error:
                        current_logging = f'No embedding received for additional feature. Error: {error}'
                        logger.warning(current_logging)
                        markers.add(None)
                        is_error = True
                        logging_from_marked += f'\n\n{current_logging}'
                        continue
                    if embedding_features.size != 0:
                        marker = self.recorder.determining_importance_with_additional_feature(
                            current_feature_name,
                            current_feature_value,
                            embedding_features,
                            slice_hierarchy_true_date.shape[0],
                        )
                    else:
                        marker = None
                    markers.add(marker)
                    if marker:
                        break

            if True not in markers:
                marker, is_error, logging_from_marked = self.get_maker_by_diagnosis(
                    current_feature_name,
                    current_feature_value,
                    feature_row.diseases,
                    true_table,
                    is_error,
                    logging_from_marked,
                )
                markers.add(marker)
        return is_error, logging_from_marked

    @timing
    def get_markers_for_none_feature(
        self,
        feature_row: Series,
        true_table: DataFrame,
        patient_id: int,
        is_error: bool,
        logging_from_marked: str,
    ) -> tuple[set[Union[bool, None]], bool, str]:
        """
        It is checked whether the feature belongs to the classes, where False is automatically
        set, if it belongs, then False is adding in markers. It is checked whether the feature
        is the last in the chain in its protocol, if it belongs, then False is adding in
        markers. Otherwise, we get a paraphrase of the feature chain description and its value
        (if any) from GPT. Then we take all True features from the neighboring branch by parent,
        if there are none, we go up to the parent until we reach the end of the tree. We add up
        all True features, see what diseases they belong to. Then we add the None feature, look
        at the assessment by diseases. We compare whether there is a convergence to some disease.
        Based on the top diseases, we fill in markers in positive, negative or insignificant
        convergence .

        If at the stage of obtaining True features from the tree, not a single True feature was
        found, then we look for all trees with the same diagnosis as the diagnosis of the
        protocol, where the None feature is located. Also, all vectors are added up and
        convergence by diseases is looked for, before and after adding the None feature.

        Throughout the pipeline, we collect all errors that occurred in the code. We
        return the presence of errors and their text from the function.

        """
        markers: set[Union[bool, None]] = set()
        is_value_for_feature = self.recorder.contains_alphanumeric(feature_row.value_parent_node)

        if (feature_row.class_parent_node in DataAutoImportance.NODE_FALSE_IMPORTANCE.value) or (
            feature_row.class_parent_node in DataAutoImportance.NODE_IF_VALUE_NOT_FALSE.value
            and not is_value_for_feature
        ):
            markers.add(False)
        elif (
            settings.CHAIN_SEPARATOR not in feature_row.chain_parent_node
            and feature_row.class_parent_node in DataAutoImportance.FALSE_SINGLE_NODE.value
            and not is_value_for_feature
        ):
            markers.add(False)
        else:
            is_error, logging_from_marked = self.get_markers_for_rated_none_feature(
                feature_row,
                true_table,
                patient_id,
                markers,
                is_error,
                logging_from_marked,
            )
        return markers, is_error, logging_from_marked

    @timing
    def additional_marking(
        self,
        patient_id: int,
        is_error: bool,
        logging_from_marked: str,
    ) -> tuple[bool, str]:
        """
        Marking of None features that remained after the initial marking of protocols,
        as well as after the database correction spiders. All None and True features
        are taken for each patient.

        It is checked whether the feature belongs to the classes, where False is
        automatically set, if it belongs, then False is set. It is checked whether the
        feature is the last in the chain in its protocol, if it belongs, then False is
        set. Otherwise, we get a paraphrase of the feature chain description and its
        value (if any) from GPT. Then we take all True features from the neighboring
        branch by parent, if there are none, we go up to the parent until we reach the
        end of the tree. We add up all True features, see what diseases they belong to.
        Then we add the None feature, look at the assessment by diseases. We compare
        whether there is a convergence to some disease. Based on the top diseases, we
        fill in positive, negative or insignificant convergence. If there is convergence,
        then the feature has True importance.

        If at the stage of obtaining True features from the tree, not a single True
        feature was found, then we look for all trees with the same diagnosis as the
        diagnosis of the protocol, where the None feature is located. Also, all vectors
        are added up and convergence by diseases is looked for, before and after adding
        the None feature.

        We change attention on all feedback links of the feature to the new attention.
        We change attetion in the protocol, from where the feature was extracted, in
        all bases.

        Throughout the pipeline, we collect all errors that occurred in the code. We
        return the presence of errors and their text from the function.

        """
        current_query = QueryMarkingFeatures.ADDITIONAL_MARKING_QUERY.value.replace(
            '|patient_id|',
            str(patient_id),
        )
        data, columns = db.cypher_query(current_query)
        table_query = DataFrame(data, columns=columns)
        table_query['split_chain'] = table_query.chain_parent_node.str.split(settings.CHAIN_SEPARATOR, regex=False)

        diseases = self.get_disease_for_protocols(
            list(table_query.protocol.unique()),
            patient_id,
        )
        table_query['diseases'] = table_query.apply(
            lambda row: diseases.get(row['protocol']),
            axis=1,
        )

        true_table = table_query.loc[table_query.attention == DataImportanceFeature.TRUE_IMPORTANCE.value]
        true_table = true_table.sort_values(by='score', ascending=False)
        none_query = table_query.loc[table_query.attention == DataImportanceFeature.NONE_IMPORTANCE.value]

        for index, feature_row in none_query.iterrows():  # pylint: disable=unused-variable
            markers, is_error, logging_from_marked = self.get_markers_for_none_feature(
                feature_row,
                true_table,
                patient_id,
                is_error,
                logging_from_marked,
            )

            if True in markers:
                marker = True
            elif None in markers or not markers:
                marker = None
            else:
                marker = False

            is_error, logging_from_marked = self.update_attention_on_edge_bd(
                marker,
                feature_row.name_parent_node,
                feature_row.class_parent_node,
                feature_row.chain_parent_node,
                feature_row.value_parent_node,
                feature_row.protocol,
                patient_id,
                is_error,
                logging_from_marked,
                query=QueryMarkingFeatures.CHANGE_ATTENTION_RELATION.value,
                with_score=False,
            )

        is_error, logging_from_marked = self.additional_update_attention(
            none_query.protocol.unique(),
            patient_id,
            is_error,
            logging_from_marked,
        )
        return is_error, logging_from_marked
