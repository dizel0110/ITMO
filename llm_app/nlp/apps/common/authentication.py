# mypy: disable-error-code="attr-defined"
from typing import Any, Optional

import requests
from django.conf import settings
from django.core.cache import cache
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTStatelessUserAuthentication
from rest_framework_simplejwt.tokens import Token


class CustomJWTStatelessUserAuthentication(JWTStatelessUserAuthentication):
    """Adds check if token user has valid license"""

    def authenticate(self, request: Request) -> Optional[tuple[Any, Token]]:
        super_auth = super().authenticate(request)
        if not super_auth:
            return None
        user, token = super_auth

        user_has_license = cache.get(f'user_has_license_{user.id}')
        if user_has_license is None:
            try:
                response = requests.post(
                    settings.LICENSE_CHECK_URL,
                    json={'user_id': user.id, 'webservice_uid': settings.APPLICATION_UID},
                    timeout=settings.TIMEOUT_SHORT,
                )
                user_has_license = response.status_code == 200
                timeout = (
                    settings.LICENSE_SUCCESSFUL_CHECK_TIMEOUT
                    if user_has_license
                    else settings.LICENSE_FAILED_CHECK_TIMEOUT
                )
                cache.set(f'user_has_license_{user.id}', user_has_license, timeout=timeout)
            except requests.exceptions.ConnectionError:
                return None

        if user_has_license:
            return user, token

        return None
