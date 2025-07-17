"""
Module for calling functionalities of YandexGPT.
================================================

Classes:
----------
GPT :
    get_operation_result\n
    get_async_result\n
    request_llm\n
    async_request_llm\n
    sync_request_llm\n
    make_request

Dependencies:
-------------
json\n
logging\n
requests\n
time\n
typing

"""

import logging
import time
from json.decoder import JSONDecodeError
from typing import Any, Union, cast

import requests
from django.core.cache import cache

from akcent_graph.apps.secret_settings.models import YGPTSettings
from akcent_graph.utils.clients.gpt.helpers import TemperatureYandexGPT
from akcent_graph.utils.clients.gpt.serializers import YGPTAsyncOperationResultSerializer
from akcent_graph.utils.clients.gpt.yandex_chain.YandexGPT_errors import DataErrorsYandexGPT
from akcent_graph.utils.timing import timing

from .yandex_chain import YandexEmbeddings, YandexLLM

logger = logging.getLogger(__name__)


class GPT:
    """
    Requests for YandexGPT.
    =======================

    Methods:
    --------
    __init__\n
    get_operation_result\n
    get_async_result\n
    request_llm\n
    async_request_llm\n
    sync_request_llm\n
    make_request

    """

    @timing
    def __init__(
        self,
        model_type: str = 'full',
        request_type: str = 'async',
        max_tokens: int = 1500,
    ) -> None:
        ygpt_settings = YGPTSettings.objects.first()
        if ygpt_settings:
            api_key = cast(str, ygpt_settings.api_key)
            folder_id = cast(str, ygpt_settings.folder_id)
        self.ygpt_settings = ygpt_settings

        self.embedder = YandexEmbeddings(
            sleep_interval=0.11,
            folder_id=folder_id,
            api_key=api_key,
        )
        self.llm = YandexLLM(
            temperature=TemperatureYandexGPT.SIMPLE_RESPONSE.value,
            folder_id=folder_id,
            api_key=api_key,
            model_type=model_type,
            request_type=request_type,
            max_tokens=max_tokens,
        )

    @timing
    def get_operation_result(
        self,
        full_url: str,
        headers: dict[str, str],
        request_timeout: float,
    ) -> dict[str, Any]:
        """Get YandexGPT results by url"""
        try:
            response = requests.get(
                full_url,
                headers=headers,
                timeout=request_timeout,
            )
        except (requests.Timeout, requests.ConnectionError) as e:
            logger.warning('Yandex GPT request return error: %s', e)
            return {}

        try:
            result = response.json()
        except JSONDecodeError as error:
            logger.error('JSON decoding error: %s. Response: %s', error, response)
            result = {}
        return result

    @timing
    def get_async_result(self, request_id: str) -> Union[str, dict[Any, Any]]:
        """
        Connect Yandex GPT, ask for a response by id, until there
        is a response. Receive only the text of the response.

        """
        if self.ygpt_settings:
            headers = cast(
                dict[str, str],
                {'Authorization': self.ygpt_settings.headers},
            )
            request_timeout = cast(
                float,
                self.ygpt_settings.request_timeout,
            )
            url_operation_result_prefix = cast(
                str,
                self.ygpt_settings.url_operation_result_prefix,
            )
            timeout = self.ygpt_settings.response_timeout_async

        full_url = f'{url_operation_result_prefix}{request_id}'

        request_processed = False
        async_llm_result = None
        time_has_passed = 0
        while not request_processed and time_has_passed < timeout:
            time.sleep(1)
            time_has_passed += 1
            async_llm_result = self.get_operation_result(full_url, headers, request_timeout)
            request_processed = async_llm_result.get('done')
            if not request_processed and async_llm_result.get('error'):
                logger.warning(
                    'Error when receiving asynchronous request response. Errror: %s',
                    async_llm_result,
                )
                if isinstance(async_llm_result['error'], str):
                    logger.warning(
                        'Error not related to http connection processing',
                    )
                    request_processed = True
                elif (
                    async_llm_result['error'].get('httpCode')
                    != DataErrorsYandexGPT.RESOURCE_EXHAUSTED.value['httpCode']  # noqa: E501, W503
                ):
                    logger.warning(
                        'Unknown asynchronous response error.',
                    )
                    request_processed = True

        serializer = YGPTAsyncOperationResultSerializer(data=async_llm_result)
        if not serializer.is_valid():
            logger.error(
                'Yandex GPT: the response from the API does not contain the expected fields %s. Response answer: %s',
                serializer.errors,
                async_llm_result,
            )
            if time_has_passed == timeout:
                logger.error(
                    'YandexGPT stopped responding to requests for more than %s seconds. Responce: %s',
                    timeout,
                    async_llm_result,
                )
            return ''

        if async_llm_result:
            if async_llm_result['response']['alternatives']:
                text_result = async_llm_result['response']['alternatives'][0]['message']['text']
                return text_result

        logger.error(
            'Yandex GPT: the response from the API does not contain empty list in alternatives: %s',
            async_llm_result,
        )
        return ''

    @timing
    def request_llm(
        self,
        prompt: str,
        system_promt: Union[str, None] = None,
    ) -> str:
        """
        Function of initial request to llm.
        For a request need to send prompt and system prompt (optional).

        """
        self.llm.instruction_text = system_promt
        llm_answer = self.llm(prompt)  # NOTE: system prompt usually passed to llm.instruction_text
        logger.debug('%s', llm_answer)
        return llm_answer

    @timing
    def async_request_llm(
        self,
        prompt: str,
        system_promt: Union[str, None] = None,
    ) -> str:
        """
        Only asynchronous requests to llm with waiting for a response.
        For a request need to send prompt and system prompt (optional).

        """
        if self.ygpt_settings:
            default_async = self.ygpt_settings.async_quota_per_hour
        else:
            default_async = 0
        async_quota_per_hour = cache.get(
            'async_quota_per_hour',
            default=default_async,
        )
        cache.set(
            key='async_quota_per_hour',
            value=async_quota_per_hour - 1,
            timeout=60 * 60,
        )

        id_llm_answer = self.request_llm(prompt, system_promt)
        return self.get_async_result(id_llm_answer)

    @timing
    def sync_request_llm(
        self,
        prompt: str,
        system_promt: Union[str, None] = None,
    ) -> str:
        """
        Only synchronous requests to llm with existing restrictions.
        For a request need to send prompt and system prompt (optional).
        ---------------------------------------------------------------

        See also:
        If quota per hour is over, switching to an asynchronous request.

        """
        if self.ygpt_settings:
            default_sync = self.ygpt_settings.sync_quota_per_hour
            default_simultaneous = self.ygpt_settings.simultaneous_generations
            timeout = self.ygpt_settings.sync_queue_timeout
        else:
            default_sync = 0
            default_simultaneous = 1
            timeout = 10

        sync_quota_per_hour = cache.get(
            'sync_quota_per_hour',
            default=default_sync,
        )

        if sync_quota_per_hour > 0:
            simultaneous_generations = cache.get(
                key='simultaneous_generations',
                default=default_simultaneous,
            )

            time_has_passed = 0
            while simultaneous_generations < 0 and time_has_passed < timeout:
                time.sleep(1)
                time_has_passed += 1
                simultaneous_generations = cache.get(
                    'simultaneous_generations',
                )

            if simultaneous_generations > 0:
                cache.set(
                    key='simultaneous_generations',
                    value=simultaneous_generations - 1,
                )

                cache.set(
                    key='sync_quota_per_hour',
                    value=sync_quota_per_hour - 1,
                    timeout=60 * 60,
                )

                answer_llm = self.request_llm(prompt, system_promt)

                cache.set(
                    key='simultaneous_generations',
                    value=cache.get('simultaneous_generations') + 1,
                )

                return answer_llm

            logger.error(
                'YandexGP lite waited for the stream queue for over %s seconds',
                timeout,
            )

        self.llm.request_type = 'async'
        return self.async_request_llm(prompt, system_promt)

    @timing
    def make_request(
        self,
        prompt: str,
        system_prompt: Union[str, None] = None,
    ) -> str:
        """
        Make a request to Yandex GPT.
        For a request need to send prompt, system prompt (optional)
        and number_attempts (optional).

        """
        if self.llm.request_type == 'sync':
            return self.sync_request_llm(prompt, system_prompt)
        if self.llm.request_type == 'async':
            return self.async_request_llm(prompt, system_prompt)

        logger.error('Model llm type "%s" does not exist.', self.llm.request_type)
        return ''
