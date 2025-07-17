"""
Module for annoy similarity from embeddings.
============================================

Classes:
----------
AnnoySimilary :
    \n\tsimilarity_with_pkl
    \n\tsimilarity_with_ann

Dependencies:
-------------
annoy
\nconstance
\npandas
\ntyping
\ntannoy

"""


from typing import Any, Literal, Optional, Union

import pandas as pd
from annoy import AnnoyIndex

from akcent_graph.utils.timing import timing


class AnnoySimilary:
    """
    Similarity of embeddings from pkls or ann using annoy.
    ======================================================

    Methods:
    --------
    \n\t__init__
    \n\tsimilarity_with_pkl
    \n\tget_data_without_score_dynamic
    \n\tget_data_with_score_dynamic
    \n\tsimilarity_with_ann
    \n\tget_data_without_score_static
    \n\tget_data_with_score_static

    """

    @timing
    def __init__(
        self,
        embedding_function: Any,
        data_df: Optional[pd.DataFrame],
        path_ann: Optional[str] = None,
        size_ann: Optional[int] = None,
        metric_ann: Optional[Literal['angular', 'euclidean', 'manhattan', 'hamming', 'dot']] = None,
    ) -> None:
        self.annoy_data = data_df
        if path_ann and size_ann and metric_ann:
            self.annoyed = AnnoyIndex(size_ann, metric_ann)
            self.annoyed.load(path_ann)
        self.embedding_function = embedding_function

    @timing
    def similarity_with_pkl(
        self,
        query: str,
        query_embedding: Optional[list[str]] = None,
        n_trees: int = 30,
        top_count: int = 20,
        how: str = 'document',
        annoy_metrics: Literal['angular', 'euclidean', 'manhattan', 'hamming', 'dot'] = 'angular',
        with_score: bool = False,
        get_names_annoy: str = 'Class' or 'name',
    ) -> Union[tuple[Optional[list[str]], Optional[dict[str, float]]], Optional[list[str]]]:
        """Get the similarity of annoy for a document and a query with a pickle."""
        if self.annoy_data is not None:
            if how == 'document':
                embeddings = self.annoy_data.embedding_document_v1.to_list()
                if not query_embedding:
                    query_embedding = self.embedding_function.embed_document(query)
            else:
                embeddings = self.annoy_data.embedding_query_v1.to_list()
                if not query_embedding:
                    query_embedding = self.embedding_function.embed_query(query)

            if query_embedding:
                embeddings.append(query_embedding)
                embedding_size = len(embeddings[0])

                annoyed = AnnoyIndex(embedding_size, annoy_metrics)
                for index, embedding in enumerate(embeddings):
                    annoyed.add_item(index, embedding)
                names = self.annoy_data[get_names_annoy].to_list()
                n_names = len(names)
                # Build the index with number_of_trees_query
                # number_of_trees_query = n_trees
                annoyed.build(n_trees)

                if with_score:
                    return self.get_data_with_score_dynamic(
                        annoyed,
                        n_names,
                        top_count,
                        names,
                    )

                return self.get_data_without_score_dynamic(
                    annoyed,
                    n_names,
                    top_count,
                    names,
                )
        if with_score:
            return [], {}
        return []

    @timing
    def get_data_without_score_dynamic(
        self,
        annoy_index: AnnoyIndex,
        index_query: int,
        top_count: int,
        names: list[str],
    ) -> list[str]:
        """Get an answer of the similarity of annoy with a list of names for dynamic data."""
        result = []
        for item in annoy_index.get_nns_by_item(index_query, top_count + 1):
            if item != index_query:
                result.append(names[item])
        return result

    @timing
    def get_data_with_score_dynamic(
        self,
        annoy_index: AnnoyIndex,
        index_query: int,
        top_count: int,
        names: list[str],
    ) -> tuple[list[str], dict[str, float]]:
        """
        Get an answer of the similarity of annoy with a score
        of the distance between the dynamic data in pkl and the incoming data
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

    @timing
    def similarity_with_ann(
        self,
        query: str,
        query_embedding: Optional[list[str]] = None,
        top_count: int = 20,
        how: str = 'document',
        with_score: bool = False,
        get_names_annoy: str = 'Class' or 'name',
    ) -> Union[tuple[list[Union[str | int]], dict[Union[str | int], float]], Optional[list[str]]]:
        """Get the similarity of annoy for a document and a query with .ann."""

        if how == 'document' and not query_embedding:
            query_embedding = self.embedding_function.embed_document(query)
        elif not query_embedding:
            query_embedding = self.embedding_function.embed_query(query)

        if query_embedding:
            if self.annoy_data:
                names = self.annoy_data[get_names_annoy].to_list()
            else:
                names = None

            if with_score:
                return self.get_data_with_score_static(
                    self.annoyed,
                    query_embedding,
                    top_count,
                    names,
                )

            return self.get_data_without_score_static(
                self.annoyed,
                query_embedding,
                top_count,
                names,
            )
        if with_score:
            return [], {}
        return []

    @timing
    def get_data_without_score_static(
        self,
        annoy_index: AnnoyIndex,
        query_embedding: Any,
        top_count: int,
        names: Optional[list[str]],
    ) -> list[Union[str | int]]:
        """
        Get an answer of the similarity of annoy with a list of names or indexes
        for static data by vector.

        """
        result: list[str | int] = []
        for item in annoy_index.get_nns_by_vector(query_embedding, top_count):
            if names:
                result.append(names[item])
            else:
                result.append(item)
        return result

    @timing
    def get_data_with_score_static(
        self,
        annoy_index: AnnoyIndex,
        query_embedding: Any,
        top_count: int,
        names: Optional[list[str]],
    ) -> tuple[list[Union[str | int]], dict[Union[str | int], float]]:
        """
        Get an answer of the similarity of annoy with a score
        of the distance between the static data in ann and the vector
        with a list of names or indexes and a dictionary of names or indexes and scores.

        """
        names_result = []
        dict_result = {}
        items, scores = annoy_index.get_nns_by_vector(
            query_embedding,
            top_count,
            include_distances=True,
        )
        for item, score in zip(items, scores):
            if names:
                name_item: Union[str | int] = names[item]
            else:
                name_item = item
            names_result.append(name_item)
            dict_result[name_item] = score
        return names_result, dict_result
