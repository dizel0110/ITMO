"""
Anamnesis processing module.
============================

Classes:
----------
ProcessingAnamnesis :
    regroup_anamnesis_dictionary\n
    get_name_and_protocols\n
    get_cluster_name\n
    remove_duplicate

Dependencies:
-------------
typing\n
uuid

"""
import uuid
from typing import Any, Union

from akcent_graph.utils.clients.clusterization.clustering_important_features import MedicalFeatureClusterer
from akcent_graph.utils.clients.gpt.call_gpt import GPT
from akcent_graph.utils.clients.gpt.prompts import get_prompt_of_anamnesis_groups


class ProcessingAnamnesis:
    """
    Class of processing anamnesis.
    ==============================

    Methods:
    --------
        __init__\n
        regroup_anamnesis_dictionary\n
        get_name_and_protocols\n
        get_cluster_name\n
        remove_duplicate

    """

    def __init__(
        self,
        model_type_gpt: str = 'lite',
        request_type_gpt: str = 'sync',
        repeat_request: int = 6,
        n_clusters: int = 10,
        linkage: str = 'ward',
        auto_optimize: bool = True,
    ) -> None:
        self.clusterizator = MedicalFeatureClusterer(
            n_clusters=n_clusters,
            linkage=linkage,
            auto_optimize=auto_optimize,
        )
        self.gpt = GPT(
            model_type=model_type_gpt,
            request_type=request_type_gpt,
        )
        self.repeat_request = repeat_request

    def regroup_anamnesis_dictionary(
        self,
        anamnesis_dict: dict[str, list[list[Union[str, int, uuid.UUID]]]],
        first_iteration: bool = True,
    ) -> dict[str, list[list[Union[str, int, uuid.UUID]]]]:
        """
        Clustering of features into groups.
        Obtaining a common name for groups.
        Creating a new dictionary with unifications.

        """
        name_features_and_protocols = self.get_name_and_protocols(
            anamnesis_dict,
        )
        group_features = self.clusterizator.get_features_groups(name_features_and_protocols)
        new_anamnesis = {}
        for features_in_group in group_features:
            one_anamnesis_list: list[list[Union[str, int, uuid.UUID]]] = []
            unique_names = set()
            for feature in features_in_group:
                group_id = uuid.uuid4()
                group = self.remove_duplicate(anamnesis_dict[feature])
                for entry in group:
                    if first_iteration:
                        entry.append(group_id)
                    unique_names.add(entry[1])
                one_anamnesis_list.extend(group)
            cluster_name = self.get_cluster_name(unique_names)
            new_anamnesis[cluster_name] = one_anamnesis_list
        return new_anamnesis

    def get_name_and_protocols(
        self,
        anamnesis_dict: dict[str, list[list[Any]]],
    ) -> list[tuple[str, int]]:
        """Get a unique feature name and protocol pair."""
        name_features_and_protocols = []
        for name_feature, list_features in anamnesis_dict.items():
            name_features_and_protocols.append((name_feature, list_features[0][0]))
        return name_features_and_protocols

    def get_cluster_name(self, features_in_group: set[str]) -> str:
        """Get the new cluster name from the GPT or the first name from the list of features names."""
        cluster_name = ''
        if len(features_in_group) > 1:
            prompt = get_prompt_of_anamnesis_groups(features_in_group)
            current_repeat_request = 0
            while not cluster_name or current_repeat_request > self.repeat_request:
                cluster_name = self.gpt.make_request(prompt)
                current_repeat_request += 1
        if not cluster_name:
            cluster_name = list(features_in_group)[0]
        cluster_name = cluster_name.replace("'", '')
        return cluster_name

    def remove_duplicate(
        self,
        list_of_lists: list[Any],
    ) -> list[Any]:
        """Remove duplicate lists, order is not preserved."""
        without_duplicate = []
        for current_tuple in set(map(tuple, list_of_lists)):  # pylint: disable=bad-builtin
            without_duplicate.append(list(current_tuple))
        return without_duplicate
