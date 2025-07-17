import logging
from typing import Any

from nlp.apps.secret_settings.models import LLMSettings
from nlp.utils.LLM.feature_extactor.feature_extractor import AnswerParsingError
from nlp.utils.LLM.llm_request import AsyncLocalLLM

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """
    Requests for LLM via API.

    Initializes the API call and the database with the LLM settings.
    request_llm method is called with a prompt argument holding the request as a single string.
    The output is given as a string.
    """

    def __init__(self) -> None:
        self.LLM = AsyncLocalLLM()
        self.llm_settings = LLMSettings.objects.get(name='embedder')
        self.llm_response: dict[str, Any] = {}

    async def embed_document(
        self,
        request: str,
    ) -> list[dict[str, Any]]:
        """
        Function to request LLM service via API with a single string prompt.
        """

        try:
            response = await self.LLM.request_embedder(
                request=request,
                model=self.llm_settings.model,
            )
            self.llm_response = response
            embedding = response['data'][0].get('embedding', [])

            if embedding:
                logger.info('Response received for full text: %s', self.llm_response)
                return embedding
            logger.warning('No valid response for full text processing')
            return []
        except Exception as exc:  # noqa B902
            logger.error(f'Error in full text processing: {exc}')
            raise AnswerParsingError(self.llm_response)

    async def embed_query(
        self,
        request: str,
    ) -> list[dict[str, Any]]:
        """
        Function to request LLM service via API with a single string prompt.
        """

        return await self.embed_document(request)
