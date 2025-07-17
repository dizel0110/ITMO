"""
Features clusterization module.
===============================

Classes:
----------
MedicalFeatureClusterer :
    validate_parameters\n
    create_anamnesis_dataframe\n
    prepare_embeddings\n
    evaluate_clustering\n
    find_optimal_parameters\n
    optimize_and_set_parameters\n
    cluster_patient_data\n
    get_cluster_entities_with_counts\n
    analyze_protocol_clustering\n
    get_features_groups\n

Dependencies:
-------------
collections\n
django\n
itertools\n
logging\n
numpy\n
pandas\n
re\n
sklearn\n
typing\n

"""


import logging
import re
from collections import Counter, defaultdict
from itertools import product
from typing import Any, Optional, Union

import numpy as np
from django.conf import settings
from pandas import DataFrame
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import silhouette_score

from akcent_graph.apps.common.ext_webservice_adapters import NeuroAdapter
from akcent_graph.utils.clients.description_functions_for_processing_features import DescriptionFunctionProcessing
from akcent_graph.utils.clients.gpt.prompts import get_prompt_for_embedding_grouping_clusterization

logger = logging.getLogger(__name__)


class MedicalFeatureClusterer:
    """
    Class for clustering medical features of one patient.
    =====================================================

    Methods:
    --------
        __init__\n
        validate_parameters\n
        create_anamnesis_dataframe\n
        prepare_embeddings\n
        evaluate_clustering\n
        find_optimal_parameters\n
        optimize_and_set_parameters\n
        cluster_patient_data\n
        get_cluster_entities_with_counts\n
        analyze_protocol_clustering\n
        get_features_groups\n

    See also:
    ---------
    Uses the AgglomerativeClustering algorithm to group
    entities based on embeddings.

    """

    def __init__(
        self,
        n_clusters: Optional[int] = None,
        distance_threshold: Optional[float] = None,
        linkage: str = 'ward',
        auto_optimize: bool = False,
    ) -> None:
        """
        Initialization with clustering parameters.
        ==========================================

        Args:
            n_clusters (int, optional): Number of clusters. None for automatic detection.
            distance_threshold (float, optional): Distance threshold. None for using n_clusters.
            linkage (str): Relationship method ('ward', 'complete', 'average', 'single').
            auto_optimize (bool): Automatic selection of parameters.

        """
        self.adapter = NeuroAdapter()

        self.auto_optimize = auto_optimize
        self.n_clusters = n_clusters
        self.distance_threshold = distance_threshold
        self.linkage = linkage
        self.validate_parameters()

        self.max_default_n_clusters = 15
        self.min_default_n_clusters = 2
        self.default_divisor_constant_n_clusters = 5
        self.default_divisor_constant_n_clusters_for_error = 3
        self.range_divisor_constant_n_clusters = [10, 7, 5]
        self.linkage_range = ['ward', 'complete', 'average']
        self.distance_threshold_range = [None, 0.5, 1.0, 1.5]

        self.abbreviation_template = r'\b[A-ZА-ЯЁ]{2,}\b'
        self.processor = DescriptionFunctionProcessing()

    def validate_parameters(self) -> None:
        """Checking and adjusting clustering parameters."""
        if (self.n_clusters is None) == (self.distance_threshold is None) and not self.auto_optimize:
            self.n_clusters = 15
            self.distance_threshold = None

        # Checking compatibility of method='ward' with distance_threshold
        if self.linkage == 'ward' and self.distance_threshold is not None:
            self.linkage = 'average'  # Ward doesn't work with distance_threshold

    def create_anamnesis_dataframe(self, anamnesis_features: list[tuple[str, int]]) -> None:
        """
        Decrypted of abbreviations in the feature name.
        Get embeddings from adapter.
        Create a dataframe for clusterization.

        """
        data = DataFrame(
            columns=[
                'entity',
                'chain',
                'structured_feature',
                'embedding',
                'feature',
                'protocol_id',
            ],
        )
        for index, feature in enumerate(anamnesis_features):
            name_feature = feature[0]
            protocol = feature[1]

            chain = name_feature.split(settings.CHAIN_SEPARATOR)
            feature_last = chain[-1] if chain else name_feature
            if re.findall(self.abbreviation_template, feature_last):
                feature_last = self.processor.get_description_with_abbreviation(feature_last)
            readable_chain = ' > '.join(chain)
            if re.findall(self.abbreviation_template, readable_chain):
                readable_chain = self.processor.get_description_with_abbreviation(readable_chain)
            structured_feature = get_prompt_for_embedding_grouping_clusterization(
                feature_last,
                readable_chain,
            )

            embedding = self.adapter.embed_query(structured_feature)
            data.loc[index] = [
                feature_last,
                readable_chain,
                structured_feature,
                embedding,
                name_feature,
                protocol,
            ]
        self.data = data

    def prepare_embeddings(
        self,
        data: Union[list[dict[str, Any]], DataFrame],
    ) -> tuple[np.ndarray[Any, np.dtype[Any]], list[str], list[Union[int, None]]]:
        """
        Preparing embeddings from input data.
        =====================================

        Args:
            data (list/DataFrame): List or DataFrame with 'embedding' field.

        Returns:
            embeddings_array (np.ndarray): Embedding array.\n
            entities (list): Names of last nodes of features.\n
            protocols (list): Protocols numbers by features.

        """
        embeddings = []
        entities = []
        protocols = []

        # Processing data in DataFrame format
        if hasattr(data, 'iterrows'):
            for _, row in data.iterrows():
                embeddings.append(row['embedding'])
                entities.append(row['entity'])
                if 'protocol_id' in row:
                    protocols.append(row['protocol_id'])
                else:
                    protocols.append(None)
        # Processing data in dictionary list format
        else:
            for item in data:
                embeddings.append(item['embedding'])
                entities.append(item['entity'])
                protocols.append(item.get('protocol_id', None))

        if isinstance(embeddings[0], list):
            embeddings_array = np.array(embeddings)
        else:
            embeddings_array = np.stack(embeddings)
        return embeddings_array, entities, protocols

    def evaluate_clustering(
        self,
        embeddings: np.ndarray[Any, np.dtype[Any]],
        labels: np.ndarray[Any, np.dtype[Any]],
    ) -> dict[str, Any]:
        """
        Evaluation of clustering quality.
        =================================

        Args:
            embeddings (numpy.ndarray): Embedding array.
            labels (numpy.ndarray): Cluster Labels.

        Returns:
            dict: Dictionary of clustering quality metrics.

        """
        n_clusters = len(np.unique(labels))

        # If only one cluster or all points are outliers, we cannot calculate metrics
        if n_clusters <= 1 or (n_clusters == 2 and -1 in labels):
            return {'n_clusters': n_clusters, 'silhouette': -1, 'small_clusters_ratio': 1.0, 'score': -float('inf')}

        # Calculate the silhouette coefficient
        try:
            # If there are outliers, we exclude them when calculating the silhouette coefficient
            if -1 in labels:
                mask = labels != -1
                silhouette = silhouette_score(embeddings[mask], labels[mask])
            else:
                silhouette = silhouette_score(embeddings, labels)
        except Exception:  # noqa: B902
            silhouette = -1

        # Calculate the proportion of small clusters (2 or less elements)
        cluster_sizes = np.bincount(labels[labels != -1] if -1 in labels else labels)
        small_clusters = np.sum(cluster_sizes <= 2)
        small_clusters_ratio = small_clusters / n_clusters if n_clusters > 0 else 1.0

        # Calculate a combined clustering quality score
        # A high silhouette coefficient is good, but a moderate number of small clusters is also OK
        score = silhouette * 0.7 - small_clusters_ratio * 0.3  # type: ignore[operator]

        return {
            'n_clusters': n_clusters,
            'silhouette': silhouette,
            'small_clusters_ratio': small_clusters_ratio,
            'score': score,
        }

    def find_optimal_parameters(
        self,
        data: Union[list[dict[str, Any]], DataFrame],
    ) -> dict[str, Any]:
        """
        Search for optimal clustering parameters.
        =========================================

        Args:
            data (list/DataFrame): List or DataFrame of a single subject.

        Returns:
            dict: Optimal parameters: n_clusters, distance_threshold and linkage.

        """
        embeddings, _, protocols = self.prepare_embeddings(data)

        unique_protocols = set(protocols)
        if None in unique_protocols:
            unique_protocols.remove(None)
        if len(unique_protocols) <= 1:
            logger.info('Not enough protocols to optimize: %s', unique_protocols)
            return {
                'n_clusters': min(
                    self.max_default_n_clusters,
                    max(self.min_default_n_clusters, len(embeddings) // self.default_divisor_constant_n_clusters),
                ),
                'linkage': 'ward',
                'distance_threshold': None,
            }

        # Ranges of parameters to iterate over
        n_clusters_range: list[Optional[int]] = [
            max(self.min_default_n_clusters, len(embeddings) // number_of_range)
            for number_of_range in self.range_divisor_constant_n_clusters
        ]
        n_clusters_range.append(None)

        # Make sure there is no distance_threshold for the ward option
        param_combinations = []
        for current_n_cluster, current_linkage, current_distance in product(
            n_clusters_range,
            self.linkage_range,
            self.distance_threshold_range,
        ):
            if (current_n_cluster is None) != (current_distance is None):
                if not (current_linkage == 'ward' and current_distance is not None):
                    param_combinations.append((current_n_cluster, current_linkage, current_distance))

        best_score = -float('inf')
        best_params = None

        for n_clusters, linkage, distance_threshold in param_combinations:
            try:
                clusterer = AgglomerativeClustering(
                    n_clusters=n_clusters,
                    distance_threshold=distance_threshold,
                    linkage=linkage,
                )

                labels = clusterer.fit_predict(embeddings)

                evaluation = self.evaluate_clustering(embeddings, labels)

                if evaluation['score'] > best_score:
                    best_score = evaluation['score']
                    best_params = {
                        'n_clusters': n_clusters,
                        'linkage': linkage,
                        'distance_threshold': distance_threshold,
                    }

                    logger.info(
                        'New best parameters: %s.\n\nSilhouette: %.4f.\n\nSmall clusters: %.4f',
                        best_params,
                        evaluation['silhouette'],
                        evaluation['small_clusters_ratio'],
                    )

            except Exception:  # noqa: B902
                # Skipping errors for some combinations of parameters
                continue

        # If good parameters could not be found, use default values
        if best_params is None:
            best_params = {
                'n_clusters': min(
                    self.max_default_n_clusters,
                    max(self.min_default_n_clusters, len(embeddings) // self.default_divisor_constant_n_clusters),
                ),
                'linkage': 'ward',
                'distance_threshold': None,
            }
            logger.info(
                'Could not find optimal parameters, using default values: %s',
                best_params,
            )
        else:
            logger.info('Optimal parameters: %s', best_params)
        return best_params

    def optimize_and_set_parameters(
        self,
        data: Union[list[dict[str, Any]], DataFrame],
    ) -> dict[str, Any]:
        """
        Optimizes parameters and sets them for the clusterer.
        =====================================================

        Args:
            data (list/DataFrame): List or DataFrame of a single subject.

        Returns:
            dict: Optimal parameters.

        """
        best_params = self.find_optimal_parameters(data)

        self.n_clusters = best_params['n_clusters']
        self.linkage = best_params['linkage']
        self.distance_threshold = best_params['distance_threshold']
        return best_params

    def cluster_patient_data(
        self,
        data: Union[list[dict[str, Any]], DataFrame],
    ) -> dict[int, list[str]]:
        """
        Clustering data and returning results as a dictionary.
        ======================================================

        Args:
            data (list/DataFrame): List or DataFrame of a single subject.

        Returns:
            dict: {cluster_id: [entity1, entity2, ...]}

        """
        if self.auto_optimize:
            self.optimize_and_set_parameters(data)

        embeddings, entities, _ = self.prepare_embeddings(data)

        if len(embeddings) <= 1:
            return {0: entities}

        # Adjust n_clusters if necessary
        n_clusters = self.n_clusters
        if n_clusters is not None and n_clusters >= len(embeddings):
            n_clusters = max(self.min_default_n_clusters, len(embeddings) - 1)

        try:
            clusterer = AgglomerativeClustering(
                n_clusters=n_clusters,
                distance_threshold=self.distance_threshold,
                linkage=self.linkage,
            )
            labels = clusterer.fit_predict(embeddings)
        except Exception as e:  # noqa: B902
            # In case of an error, we return to safe parameters
            logger.warning('Error during clustering: %s, uses safe parameters.', e)
            safe_n_clusters = max(
                self.min_default_n_clusters,
                min(self.max_default_n_clusters, len(embeddings) // self.default_divisor_constant_n_clusters_for_error),
            )
            clusterer = AgglomerativeClustering(n_clusters=safe_n_clusters, linkage='average')
            labels = clusterer.fit_predict(embeddings)

        clusters = defaultdict(list)
        for entity, label in zip(entities, labels):
            clusters[int(label)].append(entity)

        return dict(clusters)

    def get_cluster_entities_with_counts(
        self,
        data: Union[list[dict[str, Any]], DataFrame],
    ) -> dict[int, list[tuple[str, int]]]:
        """
        Clustering with counting the frequency of entities in each cluster.
        ===================================================================

        Args:
            data (list/DataFrame): List or DataFrame of a single subject.

        Returns:
            dict: {cluster_id: [(entity1, count1), (entity2, count2), ...]}

        """
        if self.auto_optimize:
            self.optimize_and_set_parameters(data)

        embeddings, entities, _ = self.prepare_embeddings(data)

        if len(embeddings) <= 1:
            counts = Counter(entities)
            return {0: [(entity, count) for entity, count in counts.items()]}

        # Adjust n_clusters if necessary
        n_clusters = self.n_clusters
        if n_clusters is not None and n_clusters >= len(embeddings):
            n_clusters = max(self.min_default_n_clusters, len(embeddings) - 1)

        try:
            clusterer = AgglomerativeClustering(
                n_clusters=n_clusters,
                distance_threshold=self.distance_threshold,
                linkage=self.linkage,
            )
            labels = clusterer.fit_predict(embeddings)
        except Exception as e:  # noqa: B902
            # In case of an error, we return to safe parameters
            logger.warning('Error during clustering: %s, uses safe parameters.', e)
            safe_n_clusters = max(
                self.min_default_n_clusters,
                min(self.max_default_n_clusters, len(embeddings) // self.default_divisor_constant_n_clusters_for_error),
            )
            clusterer = AgglomerativeClustering(n_clusters=safe_n_clusters, linkage='average')
            labels = clusterer.fit_predict(embeddings)

        entities_by_cluster = defaultdict(list)
        for entity, label in zip(entities, labels):
            entities_by_cluster[int(label)].append(entity)

        # Counting frequencies for each cluster
        clusters_with_counts = {}
        for cluster, cluster_entities in entities_by_cluster.items():
            count = Counter(cluster_entities)
            clusters_with_counts[cluster] = [(entity, cnt) for entity, cnt in count.most_common()]

        return clusters_with_counts

    def analyze_protocol_clustering(
        self,
        data: Union[list[dict[str, Any]], DataFrame],
    ) -> dict[str, Any]:
        """
        Protocol Clustering Analysis.
        =============================

        Args:
            data (list/DataFrame): List or DataFrame of a single subject.

        Returns:
            dict: Information about the distribution of protocols across clusters.

        """
        embeddings, entities, protocols = self.prepare_embeddings(data)

        if len(embeddings) <= 1:
            return {'error': 'Not enough data for analysis.'}

        if all(protocol is None for protocol in protocols):
            return {'error': 'No information about protocols.'}

        # Adjust n_clusters if necessary
        n_clusters = self.n_clusters
        if n_clusters is not None and n_clusters >= len(embeddings):
            n_clusters = max(self.min_default_n_clusters, len(embeddings) - 1)

        try:
            clusterer = AgglomerativeClustering(
                n_clusters=n_clusters,
                distance_threshold=self.distance_threshold,
                linkage=self.linkage,
            )
            labels = clusterer.fit_predict(embeddings)
        except Exception as e:  # noqa: B902
            return {'error': f'Error during clustering: {e}'}

        protocol_cluster_distribution: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for protocol, cluster in zip(protocols, labels):
            if protocol is not None:
                protocol_cluster_distribution[protocol][cluster] += 1

        protocol_cluster_percentage = {}
        for protocol, clusters in protocol_cluster_distribution.items():
            total = sum(clusters.values())
            percentage = {cluster: count / total * 100 for cluster, count in clusters.items()}
            protocol_cluster_percentage[protocol] = percentage

        # Finding the dominant cluster for each protocol
        dominant_clusters = {}
        for protocol, clusters in protocol_cluster_distribution.items():
            dominant_cluster = max(clusters.items(), key=lambda x: x[1])[0]
            dominant_clusters[protocol] = {
                'cluster': dominant_cluster,
                'count': clusters[dominant_cluster],
                'percentage': protocol_cluster_percentage[protocol][dominant_cluster],
            }

        return {
            'protocol_cluster_distribution': dict(protocol_cluster_distribution),
            'protocol_cluster_percentage': protocol_cluster_percentage,
            'dominant_clusters': dominant_clusters,
        }

    def get_features_groups(
        self,
        anamnesis_features: list[tuple[str, int]],
    ) -> list[list[str]]:
        """
        Getting a dataframe for clustering. Clustering.
        Creating groups of features, not the latest nodes.

        """
        self.create_anamnesis_dataframe(anamnesis_features)
        features_clasterization = self.cluster_patient_data(self.data)

        group_features = []
        for clasterization_entities in features_clasterization.values():
            current_list_features = []
            unique_clasterization_entities = set(clasterization_entities)
            for entity in unique_clasterization_entities:
                current_list_features.extend(self.data.loc[self.data.entity == entity, 'feature'].to_list())

            group_features.append(current_list_features)
        return group_features
