"""
Module for annoy similarity from embeddings.
============================================

Classes:
----------
DataNameClasses
\nAnnoyData :
    get_class
AnnoySimilary :
    similarity

Dependencies:
-------------
annoy
\ndataclasses
\nenum
\npandas
\npickle
\ntime
\ntyping

"""


import dataclasses
import time
from pickle import UnpicklingError
from typing import Any, Literal, Optional, Union

import pandas as pd
from annoy import AnnoyIndex

from nlp.settings import ANNOY_DATA_PATH


@dataclasses.dataclass
class AnnoyData:
    """
    Filter in dataframe for embeddings from pkls.
    =============================================

    Methods:
    --------
    get_class

    """

    data: pd.DataFrame

    def get_class(self, name: str) -> pd.DataFrame:
        return self.data[self.data.name_class == name]


class AnnoySimilary:
    """
    Similarity of embeddings from pkls using annoy.
    ===============================================

    Methods:
    --------
    \n\t__init__
    \n\tsimilarity
    \n\tget_data_without_score
    \n\tget_data_with_score

    """

    def __init__(self, embedding_function: Any, data_path: str = ANNOY_DATA_PATH) -> None:
        try:
            with open(data_path, 'rb') as file:
                temp_data = pd.read_pickle(file)
        except (EOFError, UnpicklingError):
            time.sleep(20)
            with open(data_path, 'rb') as file:
                temp_data = pd.read_pickle(file)
        self.annoy_data = AnnoyData(data=temp_data)
        self.embedding_function = embedding_function

    async def similarity(
        self,
        query: str,
        name_class: str,
        query_embedding: Optional[list[str]] = None,
        n_trees: int = 30,
        top_count: int = 20,
        how: str = 'document',
        with_score: bool = False,
        annoy_metrics: Literal['angular', 'euclidean', 'manhattan', 'hamming', 'dot'] = 'angular',
    ) -> Union[list[str], tuple[list[str], dict[str, float]]]:
        """
        Get the similarity of annoy for a document and a query with a score
        of the distance between the data in pkl and the incoming data.

        """
        data = self.annoy_data.get_class(name_class)
        if how == 'document':
            embeddings = data.embedding_document_v1.to_list()
            if not query_embedding:
                query_embedding = await self.embedding_function.embed_document(query)
            embeddings.append(query_embedding)
        else:
            embeddings = data.embedding_query_v1.to_list()
            if not query_embedding:
                query_embedding = await self.embedding_function.embed_query(query.lower())
            embeddings.append(query_embedding)
        embedding_size = len(embeddings[0])

        annoyed_v1 = AnnoyIndex(embedding_size, annoy_metrics)
        for index, embedding in enumerate(embeddings):
            annoyed_v1.add_item(index, embedding)

        names = data.Class.to_list()
        n_names = len(names)
        # Build the index with number_of_trees_query_v1
        # number_of_trees_query_v1 = n_trees
        annoyed_v1.build(n_trees)

        if with_score:
            return self.get_data_with_score(
                annoyed_v1,
                n_names,
                top_count,
                names,
            )

        return self.get_data_without_score(
            annoyed_v1,
            n_names,
            top_count,
            names,
        )

    def get_data_without_score(
        self,
        annoy_index: AnnoyIndex,
        index_query: int,
        top_count: int,
        names: list[str],
    ) -> list[str]:
        """Get an answer of the similarity of annoy with a list of names."""
        result = []
        for item in annoy_index.get_nns_by_item(index_query, top_count + 1):
            if item != index_query:
                result.append(names[item])
        return result

    def get_data_with_score(
        self,
        annoy_index: AnnoyIndex,
        index_query: int,
        top_count: int,
        names: list[str],
    ) -> tuple[list[str], dict[str, float]]:
        """
        Get an answer of the similarity of annoy with a score
        of the distance between the data in pkl and the incoming data
        with a list of names and a dictionary of names and scores.

        """
        names_result = []
        dict_result = {}
        items, scores = annoy_index.get_nns_by_item(
            index_query,
            top_count + 1,
            include_distances=True,
        )
        for item, score in zip(items, scores):
            if item != index_query:
                name_item = names[item]
                names_result.append(name_item)
                dict_result[name_item] = score
        return names_result, dict_result
