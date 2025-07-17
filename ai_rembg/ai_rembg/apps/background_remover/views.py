import uuid

from constance import config
from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ai_photoenhancer.apps.background_remover.models import ImageInfo
from ai_photoenhancer.utils.storage_tools import get_s3_client


class UploadLinkView(APIView):
    def get(self, request: Request) -> Response:
        filename = f'{uuid.uuid4()}'
        client = get_s3_client()
        presigned_url = client.generate_presigned_url(
            'put_object',
            Params={'Bucket': config.STORAGE_NAME, 'Key': f'{config.EXAMPLES_PATH}{filename}'},
            ExpiresIn=settings.UPLOAD_LINK_LIFETIME,
        )
        image_info = ImageInfo.objects.create(
            user_id=request.user.id,
            filename=filename,
        )
        return Response(
            {
                'presigned_url': presigned_url,
                'image_id': image_info.pk,
            },
        )


class DownloadLinkView(APIView):
    def get(self, request: Request, image_id: int) -> Response:
        image_info = get_object_or_404(ImageInfo, id=image_id)
        if request.user.id != image_info.user_id:
            raise Http404
        client = get_s3_client()
        presigned_url = client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': config.STORAGE_NAME,
                'Key': f'{config.RESULTS_PATH}{image_info.filename}{config.RESULT_FILENAME_POSTFIX}.png',
            },
            ExpiresIn=settings.UPLOAD_LINK_LIFETIME,
        )
        image_info.requested_at = timezone.now()
        image_info.save()

        return Response({'presigned_url': presigned_url})
