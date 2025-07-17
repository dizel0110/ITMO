"""
Module for calling functionalities of sber GigaChat.
================================================

Classes:
----------
GigaChat:
    \n\tgen_token
    \n\tget_embedding
    \n\tembed_query

Dependencies:
-------------
ast
\njson
\nlogging
\nrequests
\ntyping
\nurllib3
\nuuid

"""

import ast
import json
import logging
import uuid
from typing import Optional, cast

import requests
import urllib3
from django.conf import settings
from django.core.cache import cache

from akcent_graph.apps.secret_settings.models import GigaChatSettings
from akcent_graph.utils.timing import timing

logger = logging.getLogger(__name__)


class GigaChat:
    """
    GigaChat for getting embeddings.
    ================================

    Methods:
    --------
    \n\t__init__
    \n\tgen_token
    \n\tget_embedding
    \n\tembed_query

    """

    @timing
    def __init__(self) -> None:
        # Create an instance of the classifier
        # Load the model from the file
        gigachat_settings = GigaChatSettings.objects.first()
        if gigachat_settings:
            self.api_key = cast(str, gigachat_settings.api_key)
            self.auth_url = cast(str, gigachat_settings.auth_url)
            self.text_embedding_url = cast(str, gigachat_settings.text_embedding_url)
        self.gigachat_settings = gigachat_settings
        # Delete Unverified HTTPS request is being made to host 'gigachat.devices.sberbank.ru'.
        # Adding certificate verification is strongly advised.
        urllib3.disable_warnings()

    @timing
    def gen_token(self) -> Optional[str]:
        rquid = str(uuid.uuid4())

        payload = 'scope=GIGACHAT_API_CORP'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'RqUID': rquid,
            'Authorization': f'Basic {self.api_key}',
        }
        try:
            response = requests.post(
                self.auth_url,
                headers=headers,
                data=payload,
                verify=False,
                timeout=settings.TIMEOUT_SHORT,
            )
            ans = ast.literal_eval(response.text)
            if ans:
                token = ans.get('access_token')
            else:
                token = None
        except (requests.Timeout, requests.ConnectionError, SyntaxError) as e:
            logger.warning(
                'Error when receiving authorisation response from GigaChat: %s',
                e,
            )
            token = None

        return token

    @timing
    def get_embedding(self, text: str) -> Optional[list[float]]:
        token = cache.get(
            'GigaChat_Token',
        )
        if token is None:
            token = self.gen_token()
            cache.set(
                key='GigaChat_Token',
                value=token,
                timeout=60 * 20,
            )

        payload = json.dumps({'model': 'Embeddings', 'input': text})
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': f'Bearer {token}'}
        try:
            response = requests.post(
                self.text_embedding_url,
                headers=headers,
                data=payload,
                verify=False,
                timeout=settings.TIMEOUT_SHORT,
            )

            ans = ast.literal_eval(response.text)
            result = ans.get('data')
            if result:
                result = result[0].get('embedding')
            else:
                logger.warning(
                    'Error appears, during GigaChat response data extraction, current response.text: %s',
                    response.text,
                )
                result = None

        except (requests.Timeout, requests.ConnectionError, SyntaxError) as e:
            logger.warning(
                'Error when receiving embedding response from GigaChat: %s',
                e,
            )
            result = None

        return result

    @timing
    def embed_query(self, text: str) -> list[float]:
        """Method for getting embedding for annoy."""
        embedding = self.get_embedding(text)

        waiting_time = 0
        if self.gigachat_settings:
            timeout = self.gigachat_settings.queue_timeout
        else:
            timeout = 20

        while not embedding and waiting_time < timeout:
            embedding = self.get_embedding(text)
            waiting_time += 1
        return embedding
