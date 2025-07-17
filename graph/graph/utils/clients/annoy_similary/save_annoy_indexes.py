"""
Module for saving of annoy build for pkls.
============================================

Classes:
----------
SaveAnnoyIndexesPkl :
    save_indexes_pkl

Dependencies:
-------------
annoy
\npandas
\ntyping
\ntannoy

"""

from typing import Literal

import pandas as pd
from annoy import AnnoyIndex

from akcent_graph.utils.timing import timing


class SaveAnnoyIndexesPkl:
    """
    Saving pkl how annoy build (.ann).
    ==================================

    Methods:
    --------
    \n\tsave_indexes_pkl

    """

    @timing
    def save_indexes_pkl(
        self,
        data_path: str,
        save_data_path: str,
        n_trees: int = 30,
        how: str = 'document',
        annoy_metrics: Literal['angular', 'euclidean', 'manhattan', 'hamming', 'dot'] = 'angular',
    ) -> int:
        data = pd.read_pickle(data_path)

        if how == 'document':
            embeddings = data.embedding_document_v1.to_list()
        else:
            embeddings = data.embedding_query_v1.to_list()
        embedding_size = len(embeddings[0])

        annoyed = AnnoyIndex(embedding_size, annoy_metrics)
        for index, embedding in enumerate(embeddings):
            annoyed.add_item(index, embedding)

        annoyed.build(n_trees)
        annoyed.save(save_data_path)
        return embedding_size
