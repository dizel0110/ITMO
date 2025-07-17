from django.urls import path

from nlp.apps.protocol.views import ManageMainProcessView, ProtocolView

app_name = 'protocol'

urlpatterns = [
    path('', ProtocolView.as_view(), name='protocol'),
    path('processing/manage/<str:action>', ManageMainProcessView.as_view(), name='manage_processing'),
]
