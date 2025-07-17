# mypy: disable-error-code="union-attr"
from typing import Any, Optional

import requests
from django.conf import settings
from rest_framework import status

from nlp.apps.common.ext_webservice_auth import get_ext_webservice_token
from nlp.apps.protocol.models import Protocol, ProtocolStructureError
from nlp.apps.protocol.serializers import ProtocolGraphDBSerializer


class Error404(Exception):
    pass


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

    def _send_request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        request = requests.Request(
            method=method,
            url=url,
            **kwargs,
        )
        return self.session.send(
            self.session.prepare_request(request),
            timeout=settings.TIMEOUT_SHORT,
        )


class GraphDBAdapter(ExternalWebserviceAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.base_url = settings.GRAPHDB_PROTOCOL_BACKEND

    def post_protocol(self, protocol: Protocol) -> None:
        url = f'{self.base_url}/medaggregator/upload_protocol/'
        payload = ProtocolGraphDBSerializer(protocol).data
        response = self._send_request(
            'POST',
            url,
            json=payload,
        )
        if response.status_code == status.HTTP_201_CREATED:
            protocol.is_sent_to_graphdb = True
            protocol.is_saved_to_graphdb = True
            protocol.save()
            if warnings := response.json():
                ProtocolStructureError.objects.create(
                    protocol=protocol,
                    errors=warnings,
                )
            return
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            ProtocolStructureError.objects.create(
                protocol=protocol,
                errors=response.json(),
            )
            return
        response.raise_for_status()

    def get_structure(self) -> dict[str, Any]:
        url = f'{self.base_url}/medaggregator/structure/'
        response = self._send_request(
            'GET',
            url,
        )
        response.raise_for_status()
        return response.json()
