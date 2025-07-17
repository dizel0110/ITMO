import logging
from typing import Any, Optional

from django.conf import settings
from numpy import array
from pandas import DataFrame, Series

from akcent_graph.utils.clients.annoy_recommender.medical_records import AnnoyMedicalRecords
from akcent_graph.utils.clients.description_functions_for_processing_features import DescriptionFunctionProcessing
from akcent_graph.utils.timing import timing

logger = logging.getLogger(__name__)


class ProcessingMedicalRecords:
    @timing
    def __init__(
        self,
        data_path_df: Optional[str] = None,
        data_path_ann: Optional[str] = None,
        size_ann: Optional[int] = None,
        metric_ann: Optional[str] = None,
        positive_feature_boundary: float = settings.POSITIVE_FEATURE_BOUNDARY,
        negative_feature_boundary: float = settings.NEGATIVE_FEATURE_BOUNDARY,
    ) -> None:
        self.top_count = 5
        self.count_trees = 80
        self.processor = DescriptionFunctionProcessing()
        self.annoy = AnnoyMedicalRecords(
            data_path_df,
            data_path_ann,
            size_ann,
            metric_ann,
            positive_feature_boundary,
            negative_feature_boundary,
            self.top_count,
            self.count_trees,
        )

    @timing
    def determining_feature_importance(
        self,
        feature_name: str,
        feature_value: Optional[str],
    ) -> tuple[Optional[bool], dict[str, float]]:
        if feature_value:
            description = self.processor.get_description_feature(feature_name, feature_value)

            if description:
                marker, symptom_score = self.annoy.get_feature_importance(description)
                return marker, symptom_score
            return None, {}
        return False, {}

    @timing
    def get_name_value_from_row_feature(
        self,
        row_feature: Series,
    ) -> tuple[str, str]:
        name = row_feature.split_chain[0]
        value = f"{', '.join(row_feature.split_chain[1:])} {str(row_feature.value_parent_node).replace('[', '').replace(']', '')}"
        return name, value

    @timing
    def get_feature_embedding(
        self,
        feature_name: str,
        feature_value: str,
    ) -> Optional[list[float]]:
        if feature_name and not feature_value:
            description = self.processor.get_description_feature(
                feature_value,
                feature_name,
            )
        else:
            description = self.processor.get_description_feature(
                feature_name,
                feature_value,
            )

        if description:
            return self.annoy.gpt.get_embedding(description)
        return None

    @timing
    def get_iteration_sum(self, iteration_table: DataFrame) -> Any:
        fisrt_row = iteration_table.iloc[0]
        first_feature_name, first_feature_value = self.get_name_value_from_row_feature(
            fisrt_row,
        )
        embedding_features = array(
            self.get_feature_embedding(
                first_feature_name,
                first_feature_value,
            ),
        )

        for index, feature_row in iteration_table[1:].iterrows():  # pylint: disable=unused-variable
            feature_name, feature_value = self.get_name_value_from_row_feature(
                feature_row,
            )
            embedding = self.get_feature_embedding(
                feature_name,
                feature_value,
            )
            if embedding:
                embedding_features += array(embedding)
        return embedding_features

    @timing
    def determining_importance_with_additional_feature(
        self,
        current_feature_name: str,
        current_feature_value: str,
        embedding_features: Any,
        size: int,
    ) -> Optional[bool]:
        embedding_feature = self.get_feature_embedding(
            current_feature_name,
            current_feature_value,
        )
        if not embedding_feature:
            return None

        logger.info(
            'Below are the scores for the feature: "%s %s".',
            current_feature_name,
            current_feature_value,
        )
        markers = self.annoy.get_importance_from_feature_sums(
            embedding_features,
            size,
            embedding_feature,
        )
        logger.info(
            'End of feature scores: "%s %s".',
            current_feature_name,
            current_feature_value,
        )

        if True in markers:
            return True
        if None in markers:
            return None
        return False

    def contains_alphanumeric(self, input_string: str) -> bool:
        """Checks whether a string contains at least one alphanumeric character."""
        return any(char.isalnum() for char in input_string)

    def trim_string(self, text: str, searching: str) -> str:
        """
        Trims a string from the right up to and including
        the first occurrence of a specified character.

        """
        last_index = text.rfind(searching)
        if last_index != -1:
            searching_text = text[:last_index]
        else:
            searching_text = text
        return searching_text
