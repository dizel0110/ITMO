import logging
from typing import Any, Optional, Union

import pandas as pd
from django.conf import settings
from numpy import array

from akcent_graph.utils.clients.annoy_similary.annoy_build import AnnoySimilary
from akcent_graph.utils.clients.gpt.call_gigachat import GigaChat
from akcent_graph.utils.timing import timing

logger = logging.getLogger(__name__)


class AnnoyMedicalRecords:
    @timing
    def __init__(
        self,
        data_path_df: Optional[str] = None,
        data_path_ann: Optional[str] = None,
        size_ann: Optional[int] = None,
        metric_ann: Optional[str] = None,
        positive_feature_boundary: float = settings.POSITIVE_FEATURE_BOUNDARY,
        negative_feature_boundary: float = settings.NEGATIVE_FEATURE_BOUNDARY,
        top_count: int = 1,
        count_trees: int = 30,
    ):
        if data_path_df:
            self.data_df = pd.read_pickle(data_path_df)
        else:
            self.data_df = data_path_df
        self.data_path_ann = data_path_ann
        self.positive_feature_boundary = positive_feature_boundary
        self.negative_feature_boundary = negative_feature_boundary
        self.gpt = GigaChat()
        self.annoy_similary = AnnoySimilary(
            self.gpt,
            self.data_df,
            self.data_path_ann,
            size_ann,
            metric_ann,
        )
        self.top_count = top_count
        self.n_trees_importance = count_trees

    @timing
    def get_feature_importance(
        self,
        feature: str,
        feature_embedding: Optional[list[str]] = None,
    ) -> tuple[Optional[bool], Optional[dict[str, float]]]:
        symptom, symptom_score = self.get_feature_data_with_score(  # pylint: disable=unused-variable
            feature,
            feature_embedding,
        )
        if symptom_score:
            score = list(symptom_score.values())[0]

            if self.positive_feature_boundary > score:
                marker = True
            elif self.negative_feature_boundary < score:
                marker = False
            else:
                marker = None
            return marker, symptom_score
        return None, symptom_score

    @timing
    def get_feature_data_with_score(
        self,
        feature: str,
        feature_embedding: Optional[list[str]] = None,
    ) -> tuple[list[Union[str | int]], dict[Union[str | int], float]]:
        if self.data_path_ann:
            symptom, symptom_score = self.annoy_similary.similarity_with_ann(
                query=feature,
                query_embedding=feature_embedding,
                top_count=self.top_count,
                how='query',
                with_score=True,
            )
        else:
            symptom, symptom_score = self.annoy_similary.similarity_with_pkl(
                query=feature,
                query_embedding=feature_embedding,
                n_trees=self.n_trees_importance,
                top_count=self.top_count,
                how='query',
                with_score=True,
            )
        return symptom, symptom_score

    @timing
    def get_importance_from_feature_sums(
        self,
        current_embedding_features: Any,
        size_current_embedding_features: int,
        new_embedding_feature: list[float],
    ) -> set[Union[bool, None]]:
        (
            symptom_features,
            symptom_score_features,
        ) = self.get_feature_data_with_score(
            '',
            list(current_embedding_features),
        )

        new_embedding = list(current_embedding_features + array(new_embedding_feature))
        symptoms, symptoms_score = self.get_feature_data_with_score(  # pylint: disable=unused-variable
            '',
            new_embedding,
        )

        markers: set[Union[bool, None]] = set()
        for symptom_feature in symptom_features:
            old_score = symptom_score_features.get(symptom_feature)
            new_score = symptoms_score.get(symptom_feature)
            if new_score and old_score:
                score = old_score - new_score

                logger.info(
                    'Before adding feature to all true: %s %s. After adding feature to all true: %s %s. Difference: %s. Size sum embedding: %s.',
                    symptom_feature,
                    old_score,
                    symptom_feature,
                    new_score,
                    score,
                    size_current_embedding_features,
                )

                if score < 0:
                    markers.add(False)
                elif size_current_embedding_features > 1 and score >= settings.DELTA_SEVERAL_ADDITIONAL_FEATURE:
                    markers.add(True)
                elif size_current_embedding_features == 1 and score >= settings.DELTA_ONE_ADDITIONAL_FEATURE:
                    markers.add(True)
                else:
                    markers.add(None)
        return markers
