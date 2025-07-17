from typing import Any

from django.conf import settings
from rest_framework.permissions import BasePermission
from rest_framework.request import Request


class IsNeuroUser(BasePermission):
    def has_permission(self, request: Request, view: Any) -> bool:
        if request.user.id == settings.NEURO_USER_ID:
            return True
        return False
