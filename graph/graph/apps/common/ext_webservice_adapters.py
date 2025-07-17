# mypy: disable-error-code="union-attr"
from typing import Any, Optional

import requests
from django.conf import settings
from django.core.cache import cache
from rest_framework import status

from akcent_graph.apps.common.ext_webservice_auth import get_ext_webservice_token


class ExternalWebserviceAdapter:
    """Class contains common methods for all external webservices"""

    def __init__(self) -> None:
        self.is_ready = False
        self.session = self._get_session()

    def _get_session(self) -> Optional[requests.Session]:
        session = requests.Session()
        token = get_ext_webservice_token()
        if not token:
            return None
        session.headers.update({'Authorization': f'Bearer {token}'})
        self.is_ready = True
        return session

    def _send_request(self, method: str, url: str, raise_for_status: bool = True, **kwargs: Any) -> requests.Response:
        request = requests.Request(
            method=method,
            url=url,
            **kwargs,
        )
        response = self.session.send(
            self.session.prepare_request(request),
            timeout=settings.TIMEOUT_SHORT,
        )
        if response.status_code == status.HTTP_401_UNAUTHORIZED:
            cache.delete('ext_webservice_assess_token')
        if raise_for_status:
            response.raise_for_status()
        return response


class NeuroAdapter(ExternalWebserviceAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.base_url = settings.NEURO_BACKEND

    def embed_query(self, input_string: str) -> list[float]:
        """Method for getting embedding for annoy."""
        url = f'{self.base_url}/api/embedder/async/'
        payload = {'input_string': input_string}
        response = self._send_request(
            'POST',
            url,
            json=payload,
        )
        return response.json()

    def post_completions_request(self, payload: dict[str, Any]) -> str:
        """
        Sends request to LLM completions API
        Args:
            payload: {
                'prompt': str,
                'temperature': Optional[float],
                'top_p': Optional[float],
                'max_tokens': Optional[int]
            }

        Returns: request uid for use with get_completions_result method
        """
        url = f'{self.base_url}/api/completions/'
        response = self._send_request(
            'POST',
            url,
            json=payload,
        )
        return response.json()

    def get_completions_result(self, request_uid: str) -> Any:
        """
        Fetches LLM response by request uid.
        Args:
            request_uid: str
        Returns: Any
        """
        url = f'{self.base_url}/api/completions/'
        params = {'request_uid': request_uid}
        response = self._send_request(
            'GET',
            url,
            params=params,
        )
        return response.json()
