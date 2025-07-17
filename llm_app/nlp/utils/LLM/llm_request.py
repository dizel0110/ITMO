"""
Module for calling functionalities of YandexGPT.
================================================

Classes:
----------
GPT :
    \n\tget_operation_result
    \n\tget_async_result
    \n\trequest_llm
    \n\tasync_request_llm
    \n\tsync_request_llm
    \n\tmake_request

Dependencies:
-------------
logging
\nrequests
\ntime
\ntyping

"""

import logging
from typing import Any

import aiohttp

from nlp.settings import EMBEDDER_SERVICE_URL, LLM_SERVICE_URL

logger = logging.getLogger(__name__)


class AsyncLocalLLM:
    """
    Requests for LLM via API.

    Initializes the API call and the database with the LLM settings.
    request_llm method is called with a prompt argument holding the request as a single string.
    The output is given as a string.
    """

    def __init__(self) -> None:
        # self.session = aiohttp.ClientSession()
        return

    async def request_llm(
        self,
        request: str,
        model: str,
        temperature: float,
        top_p: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        """
        Function to request LLM service via API with a single string prompt.
        """

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{LLM_SERVICE_URL}/v1/completions',
                headers={'Authorization': 'Bearer token_123'},
                json={
                    'model': model,
                    'prompt': request,
                    'temperature': temperature,
                    'top_p': top_p,
                    'max_tokens': max_tokens,
                },
                timeout=1200,
            ) as response:
                response_json = await response.json()

        return response_json

    async def request_embedder(
        self,
        request: str,
        model: str,
    ) -> dict[str, Any]:
        """
        Function to request LLM service via API with a single string prompt.
        """

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{EMBEDDER_SERVICE_URL}/v1/embeddings',
                headers={'Authorization': 'Bearer token_123'},
                json={
                    'model': model,
                    'input': request,
                },
                timeout=1200,
            ) as response:
                response_json = await response.json()

        return response_json
