# pylint: disable=duplicate-code
"""
Module for vector text representation of Yandex.
================================================

Classes:
----------
YandexEmbeddings:
    \n\t_getModelUri
    \n\t_embed
    \n\tembed_document
    \n\tembed_documents
    \n\tembed_query
    \n\tembed_queries

Dependencies:
-------------
langchain
\nrequests
\ntenacity
\ntyping

"""


import time
from typing import TypedDict, Unpack, cast

import requests
from langchain.embeddings.base import Embeddings
from tenacity import RetryError, Retrying, stop_after_attempt, wait_fixed

from akcent_graph.apps.secret_settings.models import YGPTSettings

from .util import YAuth, YException


class Credentials(TypedDict):
    folder_id: str
    api_key: str


class YandexEmbeddings(Embeddings):
    """
    Yandex Foundation Models for vector text representation.
    ========================================================

    Methods:
    --------
    \n\t__init__
    \n\t_getModelUri
    \n\t_embed
    \n\tembed_document
    \n\tembed_documents
    \n\tembed_query
    \n\tembed_queries

    """

    def __init__(
        self,
        sleep_interval: float = 1.0,
        retries: int = 3,
        **kwargs: Unpack[Credentials],  # type: ignore[misc]
    ) -> None:
        self.sleep_interval = sleep_interval
        self.auth = YAuth.from_dict(dict(kwargs))
        self.headers = self.auth.headers
        self.retries = retries

    def _getModelUri(self, is_document: bool = False) -> str:
        return f"emb://{self.auth.folder_id}/text-search-{'doc' if is_document else 'query'}/latest"

    def _embed(self, text: str, is_document: bool = False) -> list[float]:  # type: ignore[return-value]
        constructed_json = cast(dict[str, str], {'modelUri': self._getModelUri(is_document), 'text': text})
        ygpt_settings = YGPTSettings.objects.first()
        if ygpt_settings:
            text_embedding_url = cast(str, ygpt_settings.text_embedding_url)
            request_timeout = cast(float, ygpt_settings.request_timeout)
        try:
            for attempt in Retrying(stop=stop_after_attempt(self.retries), wait=wait_fixed(self.sleep_interval)):
                with attempt:
                    response = requests.post(
                        url=text_embedding_url,
                        json=constructed_json,
                        headers=self.headers,
                        timeout=request_timeout,
                    )
                    response_json = response.json()
                    if 'embedding' in response_json:
                        return response_json['embedding']
                    raise YException(f'No embedding found, result returned: {response_json}')
        except RetryError as exc:
            raise YException(
                f'Error computing embeddings after {self.retries} retries. Result returned:\n{response_json}',
            ) from exc

    def embed_document(self, text: str) -> list[float]:
        return self._embed(text, is_document=True)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        res = []
        for text in texts:
            res.append(self.embed_document(text))
            time.sleep(self.sleep_interval)
        return res

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text, is_document=False)

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        res = []
        for text in texts:
            res.append(self.embed_query(text))
            time.sleep(self.sleep_interval)
        return res
