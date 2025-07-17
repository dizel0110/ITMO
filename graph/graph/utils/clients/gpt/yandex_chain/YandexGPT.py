"""
Module for YnadexGPT operation via API.
=======================================

Classes:
----------
YandexLLM:
    UserMessage\n
    AssistantMessage\n
    SystemMessage\n
    _call\n
    logging_synchronous_errors\n
    get_quota_per_hour\n
    get_request_with_errors\n

Dependencies:
-------------
collections\n
django\n
json\n
langchain\n
langchain_core\n
logging\n
requests\n
typing

"""


import logging
import time
from collections.abc import Mapping
from json.decoder import JSONDecodeError
from typing import Any, Optional, cast

import langchain_core
import requests
from django.core.cache import cache
from langchain.callbacks.manager import CallbackManagerForLLMRun

from akcent_graph.apps.secret_settings.models import YGPTSettings
from akcent_graph.utils.clients.gpt.helpers import TemperatureYandexGPT
from akcent_graph.utils.clients.gpt.serializers import YGPTSyncResultSerializer
from akcent_graph.utils.clients.gpt.yandex_chain.YandexGPT_errors import DataErrorsYandexGPT

from .util import YAuth

logger = logging.getLogger(__name__)


class YandexLLM(langchain_core.language_models.LLM):
    """
    Working with YandexGPT requests via API, primary request only.
    ==============================================================

    Methods:
    --------
    UserMessage\n
    AssistantMessage\n
    SystemMessage\n
    _call\n
    logging_synchronous_errors\n
    get_quota_per_hour\n
    get_request_with_errors

    See also:
    ---------
    There are many variables and 3 properties
    to customize the YandexGPT settings.

    """

    temperature: float = TemperatureYandexGPT.SIMPLE_RESPONSE.value
    max_tokens: int = 1500
    sleep_interval: float = 1.0
    retries: int = 3
    instruction_text: Optional[str] = None
    instruction_id: Optional[str] = None
    iam_token: Optional[str] = None
    folder_id: Optional[str] = None
    api_key: Optional[str] = None
    config: Optional[str] = None
    model_type: str = 'full'
    request_type: str = 'async'

    inputTextTokens: int = 0
    completionTokens: int = 0
    totalTokens: int = 0

    @property
    def _llm_type(self) -> str:
        return 'YandexGPT'

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        """Get the identifying parameters."""
        return {'max_tokens': self.max_tokens, 'temperature': self.temperature}

    @property
    def _modelUri(self) -> str:
        if self.instruction_id and self.model_type == 'fine':
            return f'ds://{self.instruction_id}'  # NOTE: Model further trained in Yandex DataSphere
        if self.model_type == 'lite':
            return f'gpt://{self.folder_id}/yandexgpt-lite/latest'  # NOTE: YandexGPT Lite
        if self.model_type == 'summarization':
            return f'gpt://{self.folder_id}/summarization/latest'  # NOTE: Brief retelling
        return f'gpt://{self.folder_id}/yandexgpt/latest'  # NOTE: model type is full (YandexGPT Pro)

    @staticmethod
    def UserMessage(message: str) -> dict[str, str]:
        return {'role': 'user', 'text': message}

    @staticmethod
    def AssistantMessage(message: str) -> dict[str, str]:
        return {'role': 'assistant', 'text': message}

    @staticmethod
    def SystemMessage(message: str) -> dict[str, str]:
        return {'role': 'system', 'text': message}

    def _call(
        self,
        prompt: str,
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        if stop is not None:
            raise ValueError('stop kwargs are not permitted.')
        msgs: list[Mapping[Any, Any]] = []
        if self.instruction_text:
            msgs.append(self.SystemMessage(self.instruction_text))
        msgs.append(self.UserMessage(prompt))
        return self._generate_messages(msgs)

    def logging_synchronous_errors(self, is_error: bool, error_dict: dict[Any, Any]) -> bool:
        """Logging errors from YandexGPT in synchronous mode."""
        if isinstance(error_dict, str):
            logger.warning('Error not related to http connection processing: %s', error_dict)
            is_error = False
        elif error_dict.get('httpCode') == DataErrorsYandexGPT.RESOURCE_EXHAUSTED.value['httpCode']:
            if error_dict.get('message') == DataErrorsYandexGPT.SYNC_MORE_THAN_ONE.value['message']:
                time.sleep(1)
            elif error_dict.get('message') == DataErrorsYandexGPT.SYNC_QUOTA_PER_HOUR_IS_OVER.value['message']:
                logger.warning(
                    'Quota of sync requests per hour has been reached.',
                )
                is_error = False
            elif self.get_quota_per_hour() < 0:
                logger.warning(
                    'Quota of %s requests per hour has been reached. Errror: %s',
                    self.request_type,
                    error_dict,
                )
                is_error = False
            else:
                logger.warning(
                    'Unknown error %s: %s',
                    DataErrorsYandexGPT.RESOURCE_EXHAUSTED.value['httpCode'],
                    error_dict,
                )
                time.sleep(1)
        else:
            logger.warning('Unknown error: %s', error_dict)
            is_error = False
        return is_error

    def get_quota_per_hour(self) -> int:
        """Get the remaining limit of attempts to Yandex GPT by request type."""
        counts_quota = {
            'sync': cache.get('sync_quota_per_hour'),
            'async': cache.get('async_quota_per_hour'),
        }
        answer = counts_quota[self.request_type]
        if answer is None:
            return 0
        return answer

    def get_request_with_errors(
        self,
        url: str,
        headers: dict[str, str],
        json: dict[str, Any],
        timeout: float,
    ) -> Optional[dict[str, Any]]:
        """Receive a request from gpt, depending on errors."""
        is_error = True
        while is_error:
            try:
                response = requests.post(url=url, headers=headers, json=json, timeout=timeout)
            except (requests.Timeout, requests.ConnectionError) as e:
                logger.warning('Yandex GPT request return error: %s', e)
                return {}

            try:
                js = response.json()
            except JSONDecodeError as error:
                logger.error('JSON decoding error: %s. Response: %s', error, response)
                js = {}

            error_dict = js.get('error')
            if error_dict:
                is_error = self.logging_synchronous_errors(is_error, error_dict)
            else:
                is_error = False

        return js

    def _generate_messages(
        self,
        messages: list[Mapping[Any, Any]],
        return_message: bool = False,
    ) -> str:
        auth = YAuth.from_dict(dict(self))
        if not self.folder_id:
            self.folder_id = auth.folder_id
        req = {
            'modelUri': self._modelUri,
            'completionOptions': {'max_tokens': self.max_tokens, 'temperature': self.temperature},
            'messages': messages,
        }
        ygpt_settings = YGPTSettings.objects.first()
        if ygpt_settings:
            completion_sync_url = cast(str, ygpt_settings.completion_sync_url)
            completion_async_url = cast(str, ygpt_settings.completion_async_url)
            request_timeout = cast(float, ygpt_settings.request_timeout)
        url = completion_sync_url if self.request_type == 'sync' else completion_async_url

        js = self.get_request_with_errors(
            url=url,
            headers=auth.headers,
            json=req,
            timeout=request_timeout,
        )

        if js:
            if self.request_type == 'sync':
                serializer = YGPTSyncResultSerializer(data=js)
                if not serializer.is_valid():
                    logger.error(
                        'Yandex GPT: the response from the API does not contain the expected fields %s',
                        serializer.errors,
                    )
                    return ''
                result = js['result']
                usage = result['usage']
                self.totalTokens += int(usage['totalTokens'] if usage['totalTokens'].isnumeric() else 0)
                self.completionTokens += int(usage['completionTokens'] if usage['completionTokens'].isnumeric() else 0)
                self.inputTextTokens += int(usage['inputTextTokens'] if usage['inputTextTokens'].isnumeric() else 0)
                alternatives = result['alternatives']
                if alternatives:  # pylint: disable=no-else-return
                    body_alternatives = alternatives[0]
                    return body_alternatives['message'] if return_message else body_alternatives['message']['text']
                else:
                    logger.error(
                        'Yandex GPT: the response from the API does not contain empty list in alternatives: %s',
                        js,
                    )
                    return ''

            if self.request_type == 'async' and js.get('id'):
                return js['id']

            logger.error('Cannot process YandexGPT request, result received: %s', js)

        return ''
