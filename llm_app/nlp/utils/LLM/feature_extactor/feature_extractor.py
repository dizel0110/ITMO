import logging
from typing import Any, Optional

from transformers import AutoTokenizer

from nlp.apps.secret_settings.models import DBStructure, LLMSettings
from nlp.settings import LLM_TOKENIZER_DIR
from nlp.utils.LLM.llm_request import AsyncLocalLLM
from nlp.utils.LLM.prompts import get_prompt_of_feature_extraction

logger = logging.getLogger(__name__)


class AnswerParsingError(Exception):
    def __init__(self, llm_response: Optional[dict[str, Any]] = None):
        self.llm_response = llm_response


class AsyncFeatureExtractor:
    """
    Asynchronous feature extraction pipeline using database settings and optimized token-based windowing.
    """

    def __init__(self) -> None:
        self.llm = AsyncLocalLLM()
        self.llm_settings = LLMSettings.objects.get(name='feature extraction')
        self.llm_response: dict[str, Any] = {}
        self.db_classes_descriptions = DBStructure.objects.get(name='descriptions').structure
        self.classes = self.db_classes_descriptions

        self.max_tokens = self.llm_settings.max_tokens
        self.prompt_overhead = 1000
        self.min_overlap_tokens = 100
        self.tokenizer = AutoTokenizer.from_pretrained(LLM_TOKENIZER_DIR)

    def calculate_token_length(self, text: str) -> int:
        """
        Calculate the number of tokens in the text.
        """
        return len(self.tokenizer.encode(text))  # Replace with tokenizer if available

    def calculate_optimal_chunk_count(self, total_tokens: int) -> int:
        """
        Calculate the number of chunks for optimal LLM usage.
        """
        max_chunk = (self.max_tokens - self.prompt_overhead) // 4
        return max(1, (total_tokens + max_chunk - 1) // max_chunk)

    def get_chunk_by_tokens(self, text: str, start_pos: int, chunk_size: int) -> tuple[str, int]:
        """
        Extract a chunk of text based on token positions using a tokenizer.
        """
        tokens = self.tokenizer.encode(text, add_special_tokens=False)
        end_pos = min(start_pos + chunk_size, len(tokens))
        chunk_tokens = tokens[start_pos:end_pos]
        chunk = self.tokenizer.decode(chunk_tokens, skip_special_tokens=True)
        return chunk, end_pos

    async def sliding_window(self, protocol: str) -> list[str]:
        """
        Process protocol text using sliding windows and LLM API calls.
        """
        results = []
        total_tokens = self.calculate_token_length(protocol)

        chunk_count = self.calculate_optimal_chunk_count(total_tokens)
        base_chunk_size = total_tokens // chunk_count
        logger.info('Splitting text into %s chunks of ~%s tokens each', chunk_count, base_chunk_size)

        start_pos = 0
        for i in range(chunk_count):
            is_last_chunk = i == chunk_count - 1
            chunk_size = total_tokens - start_pos if is_last_chunk else base_chunk_size
            chunk, end_pos = self.get_chunk_by_tokens(protocol, start_pos, chunk_size)

            logger.info('Processing chunk %s/%s with %s tokens', i + 1, chunk_count, self.calculate_token_length(chunk))
            request_extraction = await get_prompt_of_feature_extraction(chunk, str(self.classes))
            tokens = self.tokenizer.tokenize(request_extraction)
            logger.warning(f'Request in extractor: {request_extraction}')

            # Считаем количество токенов
            num_tokens = len(tokens)
            logger.warning(f'Tokens: {num_tokens}')

            try:
                response = await self.llm.request_llm(
                    request=request_extraction,
                    model=self.llm_settings.model,
                    temperature=self.llm_settings.temperature,
                    top_p=self.llm_settings.top_p,
                    max_tokens=self.max_tokens,
                )
                self.llm_response = response
                answer = response['choices'][0].get('text', '').strip()

                if answer:
                    results.append(answer)
                else:
                    logger.warning(f'No valid response for chunk {i + 1}')
            except Exception as exc:  # noqa B902
                logger.error(f'Error processing chunk {i + 1}: {exc}')
                raise AnswerParsingError(self.llm_response)

            start_pos = end_pos - self.min_overlap_tokens if not is_last_chunk else end_pos

        return results

    def pre_processing(self, protocol: str) -> str:
        """
        Preprocess the input protocol text.
        """
        return protocol.strip() if protocol else ''

    def post_processing(self, answers: list[str]) -> list[str]:
        """
        Postprocess the LLM responses.
        """
        return [answer for answer in answers if answer]

    async def pipe(self, protocol: str, use_sliding_window: bool = True) -> Optional[list[str]]:
        """
        Main pipeline to process the input protocol text and extract features.

        Args:
            protocol: Input protocol text
            use_sliding_window: Whether to use sliding window approach
        """
        protocol = self.pre_processing(protocol)
        if not protocol:
            logger.error('Empty protocol provided')
            return None

        try:
            if use_sliding_window:
                answers = await self.sliding_window(protocol)
            else:
                answers = await self.process_full_text(protocol)
            return self.post_processing(answers)
        except Exception as exc:  # noqa B902
            logger.error(f'Error in feature extraction pipeline: {exc}')
            raise AnswerParsingError(self.llm_response)

    async def process_full_text(self, protocol: str) -> list[str]:
        """
        Process the entire protocol text in one LLM call.
        """
        logger.info('Processing full text with %s tokens', self.calculate_token_length(protocol))
        request_extraction = await get_prompt_of_feature_extraction(protocol, str(self.classes))

        try:
            response = await self.llm.request_llm(
                request=request_extraction,
                model=self.llm_settings.model,
                temperature=self.llm_settings.temperature,
                top_p=self.llm_settings.top_p,
                max_tokens=self.max_tokens,
            )
            self.llm_response = response
            answer = response['choices'][0].get('text', '').strip()

            if answer:
                logger.info('Response received for full text: %s', answer)
                return [answer]
            else:
                logger.warning('No valid response for full text processing')
                return []
        except Exception as exc:  # noqa B902
            logger.error(f'Error in full text processing: {exc}')
            raise AnswerParsingError(self.llm_response)
