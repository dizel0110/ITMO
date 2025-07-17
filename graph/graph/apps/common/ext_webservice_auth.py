import logging
from typing import Optional

import requests
from constance import config
from django.conf import settings
from django.core.cache import cache
from rest_framework import status

logger = logging.getLogger(__name__)


def get_ext_webservice_token() -> Optional[str]:
    token = cache.get('ext_webservice_assess_token', None)
    if token:
        return token
    logger.warning('External webservice token not found in cache')
    return refresh_ext_webservice_token()


def refresh_ext_webservice_token() -> Optional[str]:
    refresh_token = cache.get('ext_webservice_refresh_token', None)
    if refresh_token:
        response = requests.post(
            f'{config.LICENSE_SERVER_AUTH_BACKEND}refresh/',
            json={'refresh': refresh_token},
            timeout=settings.TIMEOUT_SHORT,
        )
        if response.status_code == status.HTTP_401_UNAUTHORIZED:
            cache.delete('ext_webservice_refresh_token')
        elif response.ok:
            json_response = response.json()
            cache.set(
                'ext_webservice_assess_token',
                json_response['access'],
                timeout=config.LICENSE_ACCESS_TOKEN_LIFETIME,
            )
            return json_response['access']

    response = requests.post(
        config.LICENSE_SERVER_AUTH_BACKEND,
        json={'username': config.LICENSE_SERVER_LOGIN, 'password': config.LICENSE_SERVER_PASSWORD},
        timeout=settings.TIMEOUT_SHORT,
    )
    if response.ok:
        json_response = response.json()
        cache.set(
            'ext_webservice_assess_token',
            json_response['access'],
            timeout=config.LICENSE_ACCESS_TOKEN_LIFETIME,
        )
        cache.set(
            'ext_webservice_refresh_token',
            json_response['refresh'],
            timeout=config.LICENSE_REFRESH_TOKEN_LIFETIME,
        )
        return json_response['access']

    return None
