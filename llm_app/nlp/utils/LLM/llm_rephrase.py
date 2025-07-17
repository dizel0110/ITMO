import logging
from typing import Any

from nlp.apps.secret_settings.models import LLMSettings
from nlp.utils.LLM.feature_extactor.feature_extractor import AnswerParsingError
from nlp.utils.LLM.llm_request import AsyncLocalLLM
from nlp.utils.LLM.prompts import get_prompt_of_rephrase

logger = logging.getLogger(__name__)


class AsyncRephrase:
    """
    Neural feature extraction pipeline.

    Initialises the API with the LLM at initialisation.
    The main functionality is in the .pipe method, which is called with an argument in the form of a protocol.
    Then the protocol is preprocessed and sent with correct system prompts to LLM for feature extraction.
    The result is parsed, cleaned and given to the function output.
    =======================

    Methods:
    --------
    \n\t__init__
    \n\tpre_processing
    \n\tpost_processing
    \n\tpipe

    """

    def __init__(
        self,
    ) -> None:
        self.llm = AsyncLocalLLM()  # Create an LLM.
        self.llm_settings = LLMSettings.objects.get(name='rephrase')
        self.llm_response: dict[str, Any] = {}

    def pre_processing(self, protocol: str) -> str:
        """
        Not implemented
        """
        return protocol

    def post_processing(self, answer: str) -> str:
        """
        Parsing the output string to get the json
        """
        return answer

    async def pipe(self, protocol: str) -> str:
        """
        Full input protocol processing pipeline:
        Pre-processing, feature extraction, post-processing.
        """
        protocol = self.pre_processing(protocol)
        if not protocol:
            logger.error('There is no protocol: %s', protocol)
            return ''
        try:
            answers = await self.protocol_rephrase(protocol)
            post_processed = self.post_processing(answers)
            if not post_processed:
                logger.error('Cannot postprocess text for the local llm in rephrase: %s', answers)
                return ''
        except KeyError as exc:
            raise AnswerParsingError(self.llm_response) from exc

        return post_processed

    async def protocol_rephrase(
        self,
        protocol: str,
    ) -> str:
        """
        Processes a large protocol text exceeding the model’s context limit using a sliding window approach.

        Parameters:
        - protocol: The main protocol text to be processed, potentially exceeding the model's context window.
        - window_size: Maximum number of tokens for each window (default is 3000 to allow space for model output).
        - overlap: Number of tokens overlapping between windows to capture cross-window dependencies (default is 500).

        Returns:
        - A full concatenated text result containing responses from all sliding windows.
        """
        # Generate the prompt for the current chunk
        request_extraction = await get_prompt_of_rephrase(protocol)
        self.llm_response = await self.llm.request_llm(
            request=request_extraction,
            model=self.llm_settings.model,
            temperature=self.llm_settings.temperature,
            top_p=self.llm_settings.top_p,
            max_tokens=self.llm_settings.max_tokens,
        )
        answers = self.llm_response['choices'][0].get('text', '')
        if not answers:
            logger.error('Empty answer from LLM.')

        return answers
