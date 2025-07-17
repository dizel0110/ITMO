from django.urls import path

from ai_photoenhancer.apps.background_remover.views import DownloadLinkView, UploadLinkView

app_name = 'background_remover'

urlpatterns = [
    path('get_upload_link/', UploadLinkView.as_view(), name='get_upload_link'),
    path('get_download_link/<int:image_id>/', DownloadLinkView.as_view(), name='get_download_link'),
]
