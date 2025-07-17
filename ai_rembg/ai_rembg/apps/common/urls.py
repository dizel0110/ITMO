from django.urls import path

from ai_photoenhancer.apps.common.views import RefreshJWTKeysView

app_name = 'common'

urlpatterns = [
    path('api/token/set_keys/', RefreshJWTKeysView.as_view(), name='refresh_jwt_keys'),
]
