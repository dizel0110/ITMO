import json
import logging
import re
from typing import Any, Optional

from nlp.apps.secret_settings.models import DBStructure, LLMSettings
from nlp.utils.LLM.Embedder import EmbeddingModel
from nlp.utils.LLM.feature_extactor.feature_extractor import AnswerParsingError
from nlp.utils.LLM.feature_extactor.tools import async_get_graphdb_structure
from nlp.utils.LLM.llm_request import AsyncLocalLLM
from nlp.utils.LLM.prompts import get_prompt_of_RAG, get_prompt_of_unification
from nlp.utils.LLM.RAG import AnnoySimilary

logger = logging.getLogger(__name__)


class AsyncFeatureUnifier:
    """
    Asynchronous unification pipeline that processes text using a reference database of entities.
    Extracts data for each class using its corresponding reference examples.
    """

    def __init__(self) -> None:
        self.llm = AsyncLocalLLM()
        self.llm_settings = LLMSettings.objects.get(name='feature unification')
        self.db_classes_descriptions = DBStructure.objects.get(name='descriptions').structure
        self.db_entities = DBStructure.objects.get(name='entities').structure
        self.class_names = list(self.db_classes_descriptions.keys())
        self.llm_response: dict[str, Any] = {}
        emb_func = EmbeddingModel()
        self.Annoy = AnnoySimilary(embedding_function=emb_func)

    def split_text_by_classes(self, text: str) -> dict[str, str]:
        """
        Split input JSON-like text into chunks based on class names.
        Handles potential artifacts in the text.

        Args:
            text: Input text containing JSON-like structures

        Returns:
            Dictionary mapping class names to their corresponding text chunks
        """
        chunks = {}
        for class_name in self.class_names:
            start_pattern = f'"{class_name}": ['
            class_start = text.find(start_pattern)
            if class_start == -1:
                continue

            content_start = class_start + len(start_pattern)
            bracket_count = 1
            content_end = content_start

            while bracket_count > 0 and content_end < len(text):
                if text[content_end] == '[':
                    bracket_count += 1
                elif text[content_end] == ']':
                    bracket_count -= 1
                content_end += 1

            if bracket_count == 0:
                content = text[content_start : content_end - 1].strip()
                if content.endswith(','):
                    content = content[:-1]
                chunks[class_name] = content

        return chunks

    def pre_processing(self, text: str) -> str:
        """
        Preprocess the input text.

        Args:
            text: Input text to process

        Returns:
            Preprocessed text
        """
        return text.strip() if text else ''

    async def RAG_process(self, query: str, class_name: str) -> str:
        answers = await self.Annoy.similarity(query, class_name)
        docs = [{'doc_id': i, 'title': None, 'content': answers[i]} for i in range(len(answers))]
        prompt = await get_prompt_of_RAG(query, docs)

        response = await self.llm.request_llm(
            request=prompt,
            model=self.llm_settings.model,
            temperature=self.llm_settings.temperature,
            top_p=self.llm_settings.top_p,
            max_tokens=self.llm_settings.max_tokens,
        )
        logger.error(f'Answer in unifier_rag: {response}')
        self.llm_response = response
        answer = response['choices'][0].get('text', '').strip()
        result_string = re.search(r'\{.*?\"relevant_doc_ids\": \[.*?\].*?\}', answer)
        if result_string:
            result = json.loads(result_string.group()).get('relevant_doc_ids', [])
        else:
            result = []

        if result:
            doc_id_to_find = result[0]
            result = next(doc['content'] for doc in docs if doc['doc_id'] == doc_id_to_find)

        return result

    async def process_by_class(self, text: str, rag: bool = True) -> list[str]:
        """
        Process text chunks by class, using corresponding reference examples.

        Args:
            text: Input text to process

        Returns:
            List of JSON strings, each containing extracted entities for a specific class
        """
        logger.warning('PROCESSING WORKS1')
        results = []
        text_chunks = self.split_text_by_classes(text)
        logger.warning('PROCESSING WORKS2')
        for class_name in self.class_names:
            class_text = text_chunks.get(class_name, '')
            if not class_text:
                logger.warning(f'No text found for class {class_name}')
                continue

            if class_name not in self.db_entities:
                logger.info(f'Class {class_name} is not present in db_entities. Skipping.')
                continue

            try:
                reference_examples = self.db_entities[class_name]
                logger.warning('All good with bd')

            except Exception as exc:  # noqa: B902
                logger.warning(f'DB parsing problem, entities: {self.db_entities}')
                logger.warning(f'DB parsing problem, class: {class_name}')
                raise exc

            prompt = await get_prompt_of_unification(f'{class_name}: {class_text}', str(reference_examples))

            try:
                logger.info(f'Processing class: {class_name}')

                if rag:
                    answer = await self.RAG_process(text, class_name)
                else:
                    response = await self.llm.request_llm(
                        request=prompt,
                        model=self.llm_settings.model,
                        temperature=self.llm_settings.temperature,
                        top_p=self.llm_settings.top_p,
                        max_tokens=self.llm_settings.max_tokens,
                    )
                    logger.error(f'Answer in unifier: {response}')
                    self.llm_response = response
                    answer = response['choices'][0].get('text', '').strip()

                if answer:
                    results.append(answer)
                else:
                    logger.warning(f'Empty response for class {class_name}')

            except Exception as exc:  # noqa: B902
                logger.error(f'Error processing class {class_name}: {exc}')
                raise AnswerParsingError(self.llm_response)

        return results

    async def pipe(self, text: str) -> Optional[list[str]]:
        """
        Process input text using database classes and entities.

        Args:
            text: Input text to process

        Returns:
            List of responses for each class

        Raises:
            AnswerParsingError: If there's an error in processing or parsing the responses
        """
        self.db_entities = await async_get_graphdb_structure()
        self.class_names = list(self.db_classes_descriptions.keys())

        text = self.pre_processing(text)
        if not text:
            logger.error('Empty input text')
            return None

        try:
            responses = await self.process_by_class(text)
            return responses
        except Exception as exc:  # noqa B902
            logger.error(f'Error in unification pipeline: {exc}')
            raise AnswerParsingError(self.llm_response)
