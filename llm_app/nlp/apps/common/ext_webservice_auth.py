from typing import Optional

import requests
from constance import config
from django.conf import settings
from django.core.cache import cache

from nlp.celeryapp import app


def get_ext_webservice_token() -> Optional[str]:
    token = cache.get('ext_webservice_assess_token', None)
    if token:
        return token
    return refresh_ext_webservice_token()


@app.task(ignore_result=True)
def refresh_ext_webservice_token() -> Optional[str]:
    refresh_token = cache.get('ext_webservice_refresh_token', None)
    if refresh_token:
        response = requests.post(
            f'{config.LICENSE_SERVER_AUTH_BACKEND}/refresh/',
            json={'refresh': refresh_token},
            timeout=settings.TIMEOUT_SHORT,
        )
        if response.ok:
            json_response = response.json()
            cache.set(
                'ext_webservice_assess_token',
                json_response['access'],
                timeout=config.LICENSE_ACCESS_TOKEN_LIFETIME,
            )
            refresh_ext_webservice_token.apply_async(queue='low', countdown=config.LICENSE_ACCESS_TOKEN_LIFETIME)
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
        refresh_ext_webservice_token.apply_async(queue='low', countdown=config.LICENSE_ACCESS_TOKEN_LIFETIME)
        return json_response['access']

    return None
