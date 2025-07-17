import json
import logging
from typing import Any, Optional

from nlp.apps.secret_settings.models import Prompt

logger = logging.getLogger(__name__)


def edit_message_llm_old(
    query: str,
    system_prompt: str,
    sample: str = '',
    example_prompt: Optional[dict[str, str]] = None,
) -> str:
    """Формирование промпта для LLM с учетом примера, если он задан."""
    prompt = f"""
<|begin_of_text|><|start_header_id|>system<|end_header_id|>
{system_prompt}<|eot_id|>
"""
    if example_prompt:
        prompt += f"""<|start_header_id|>user<|end_header_id|>
{example_prompt['example_request']}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
{example_prompt['example_answer']}<|eot_id|>
"""
    prompt += f"""<|start_header_id|>user<|end_header_id|>
{query}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"""
    prompt += sample
    return prompt


def edit_message_llm(
    query: str,
    system_prompt: str,
    sample: str = '',
    example_prompt: Optional[dict[str, str]] = None,
    documents: Optional[list[dict[str, Any]]] = None,
) -> str:
    """
    Формирование промпта для LLM с учетом примера, документов и истории сообщений.
    """
    # Начало с system сообщения
    prompt = f'system:\n{system_prompt}\n\n'

    # Добавляем документы, если они указаны
    if documents:
        prompt += f'documents:\n{json.dumps(documents, ensure_ascii=False, indent=2)}\n\n'

    # Если есть пример, добавляем его как последовательность сообщений
    if example_prompt:
        prompt += (
            f"user:\n{example_prompt['example_request']}\n\n" f"assistant:\n{example_prompt['example_answer']}\n\n"
        )

    # Добавляем основной запрос
    prompt += f'user:\n{query}\n\n'

    # Завершаем промпт, добавляя sample (если задан)
    if sample:
        prompt += f'assistant:\n{sample}'

    return prompt


async def get_prompt_of_feature_extraction(query: str, classes: str) -> str:
    """Получение и формирование промпта для feature extraction из базы данных."""
    prompt_preparation = await Prompt.objects.filter(name='feature extraction').afirst()

    if not prompt_preparation:
        logger.error('There are no feature extraction prompt in database.')
        return ''

    sys_text = prompt_preparation.system_text
    answer_format = prompt_preparation.answer_format

    format_answer = f"""Отвечай в формате:
    ```json
    {answer_format}
    ```
    """

    prompt_db_descr = f"""
    Допустимые классы:
    {classes}
    """

    wrap = """```json
    """

    short_req = f"""
    Протокол:
    {query}
    """
    full_query = sys_text + prompt_db_descr + short_req
    if not prompt_preparation.example_request_text or not prompt_preparation.example_answer_text:
        example = None
    else:
        example = {
            'example_request': sys_text + prompt_db_descr + prompt_preparation.example_request_text,
            'example_answer': prompt_preparation.example_answer_text,
        }
    return edit_message_llm(query=full_query, system_prompt=format_answer, sample=wrap, example_prompt=example)


async def get_prompt_of_rephrase(query: str) -> str:
    """Получение и формирование промпта для перефраза из базы данных."""
    prompt_preparation = await Prompt.objects.filter(name='rephrase').afirst()

    if not prompt_preparation:
        logger.error('There are no feature extraction prompt in database.')
        return ''

    return edit_message_llm(query=query, system_prompt=prompt_preparation.system_text)


async def get_prompt_of_unification(query: str, db: str) -> str:
    """Получение и формирование промпта для feature extraction из базы данных."""
    prompt_preparation = await Prompt.objects.filter(name='feature unification').afirst()

    if not prompt_preparation:
        logger.error('There are no feature extraction prompt in database.')
        return ''

    if not prompt_preparation.example_request_text or not prompt_preparation.example_answer_text:
        example = None
    else:
        example = {
            'example_request': prompt_preparation.example_request_text,
            'example_answer': prompt_preparation.example_answer_text,
        }
    sys_text = prompt_preparation.system_text
    answer_format = prompt_preparation.answer_format
    format_answer = f"""Отвечай в формате:
    ```json
    {answer_format}
    ```
    """

    prompt_db_descr = f"""
    Database:
    {db}
    """

    wrap = """```json
    """

    full_query = sys_text + prompt_db_descr

    short_req = f"""
    Json репрезентация протокола:
    {query}
    """
    full_query += short_req

    return edit_message_llm(query=full_query, system_prompt=format_answer, sample=wrap, example_prompt=example)


async def get_prompt_of_RAG(query: str, documents: Optional[list[dict[str, Any]]]) -> str:
    """Получение и формирование промпта для RAG из базы данных."""
    prompt_preparation = await Prompt.objects.filter(name='RAG').afirst()

    if not prompt_preparation:
        logger.error('There are no RAG prompt in database.')
        return ''

    if not prompt_preparation.example_request_text or not prompt_preparation.example_answer_text:
        example = None
    else:
        example = {
            'example_request': prompt_preparation.example_request_text,
            'example_answer': prompt_preparation.example_answer_text,
        }
    sys_text = prompt_preparation.system_text

    return edit_message_llm(query=query, system_prompt=sys_text, example_prompt=example, documents=documents)
