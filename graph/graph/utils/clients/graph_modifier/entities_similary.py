import dataclasses

import pandas as pd
from django.conf import settings

from akcent_graph.apps.common.ext_webservice_adapters import NeuroAdapter
from akcent_graph.utils.clients.annoy_similary.annoy_build import AnnoySimilary
from akcent_graph.utils.clients.gpt.call_gpt import GPT


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


class EntityFinder:
    """
    Semantic search for possible parent or child entities
    =====================================================

    Methods:
    --------
    \n\t__init__
    \n\tget_similary_entity

    """

    def __init__(
        self,
        gpt_model_type: str = 'lite',
        gpt_request_type: str = 'sync',
        data_path: str = settings.ENTITIES_DATA_PATH,
    ) -> None:
        self.gpt = GPT(model_type=gpt_model_type, request_type=gpt_request_type)
        self.adapter = NeuroAdapter()
        entities = pd.read_pickle(data_path)
        self.entity_data = AnnoyData(data=entities)

    def get_similary_entity(
        self,
        entity_name: str,
        name_targetclass: str,
    ) -> list[str]:
        """This method find similary entity in another class
        entity_name: name of current entity\n
        name_targetclass: name of target class for finding similary entity
        """
        entities_targetclass = self.entity_data.get_class(name=name_targetclass)
        entitysimilary = AnnoySimilary(
            embedding_function=self.adapter.embed_query,
            data_df=entities_targetclass,
        )
        entity_name_embedding = self.adapter.embed_query(entity_name)
        entities_answer = entitysimilary.similarity_with_pkl(
            query=entity_name,
            query_embedding=entity_name_embedding,
            how='query',
            get_names_annoy='name',
        )
        return entities_answer
