from typing import Optional, Union

from django.conf import settings
from numpy import array

from akcent_graph.utils.clients.annoy_recommender.medical_records import AnnoyMedicalRecords
from akcent_graph.utils.clients.gpt.call_gpt import GPT
from akcent_graph.utils.clients.gpt.prompts import get_prompt_of_description_feature
from akcent_graph.utils.timing import timing


class ProcessingMedicalRecords:
    # TODO need refactoring this class
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
        self.gpt = GPT(model_type='lite', request_type='sync', max_tokens=512)
        self.top_count = 1
        self.count_trees = 80
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
    def get_description_feature(self, name: str, meaning: str) -> str:
        """Get a paraphrase of the feature about the symptom property from gpt."""
        user_prompt = get_prompt_of_description_feature(
            name,
            meaning,
        )
        description = self.gpt.make_request(user_prompt)
        return description.replace('*', '')

    @timing
    def determining_feature_importance(
        self,
        feature_name: str,
        feature_value: Optional[str],
    ) -> tuple[Optional[bool], Optional[dict[str, float]], Optional[str]]:
        if feature_value:
            description = self.get_description_feature(feature_name, feature_value)
            if description:
                marker, symptom_score = self.annoy.get_feature_importance(description)
                return marker, symptom_score, description
            return None, {}, ''
        return False, {}, ''

    @timing
    def get_feature_embedding(
        self,
        feature: Union[str, dict[str, str]],
    ) -> tuple[Optional[list[float]], str]:
        if isinstance(feature, str):
            return self.annoy.gpt.get_embedding(feature), feature
        if isinstance(feature, dict):
            description_feature = self.get_description_feature(
                feature['имя'],
                feature['значение'],
            )
            return self.annoy.gpt.get_embedding(description_feature), description_feature
        return None, str(feature)  # type: ignore[unreachable]

    @timing
    def determining_importance_with_additional_feature(
        self,
        feature: Union[str, dict[str, str]],
        additional_feature: Optional[Union[str, dict[str, str]]],
    ) -> tuple[Optional[bool], Optional[dict[str, float]], Optional[str]]:
        embedding_feature, description_feature = self.get_feature_embedding(
            feature,
        )
        if embedding_feature:
            (
                symptom_feature,  # pylint: disable=unused-variable
                symptom_score_feature,
            ) = self.annoy.annoy_similary.similarity_with_pkl(
                query=description_feature,
                query_embedding=embedding_feature,
                n_trees=self.count_trees,
                top_count=self.top_count,
                how='query',
                with_score=True,
            )
        else:
            return None, {}, ''
        if not additional_feature:
            return None, symptom_score_feature, description_feature

        embedding_additional_feature, description_additional_feature = self.get_feature_embedding(
            additional_feature,
        )

        if embedding_feature and embedding_additional_feature:
            descriptions = f'{description_feature}\n{description_additional_feature}'
            new_embedding = list(array(embedding_feature) + array(embedding_additional_feature))

            symptom, symptom_score = self.annoy.annoy_similary.similarity_with_pkl(  # pylint: disable=unused-variable
                query=descriptions,
                query_embedding=new_embedding,
                n_trees=self.count_trees,
                top_count=self.top_count,
                how='query',
                with_score=True,
            )
            score = list(symptom_score_feature.values())[0] - list(symptom_score.values())[0]
            if score >= settings.DELTA_ONE_ADDITIONAL_FEATURE:  # pylint: disable=simplifiable-if-statement
                marker = True
            else:
                marker = False
            return marker, {'before': symptom_score_feature, 'after': symptom_score}, descriptions
        return None, {}, ''
