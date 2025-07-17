import os

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.views import View
from rest_framework import status


class RefreshJWTKeysView(LoginRequiredMixin, View):
    def get(self, request: HttpRequest) -> HttpResponse:
        private_path = os.path.join(settings.JWT_KEY_DIR, 'jwt_key.pem')
        public_path = os.path.join(settings.JWT_KEY_DIR, 'jwt_key.pub')
        if os.path.isfile(private_path):
            with open(private_path, encoding='utf8') as file:
                settings.SIMPLE_JWT['SIGNING_KEY'] = file.read()
        if os.path.isfile(public_path):
            with open(public_path, encoding='utf8') as file:
                settings.SIMPLE_JWT['VERIFYING_KEY'] = file.read()
        return HttpResponse(status=status.HTTP_200_OK)
