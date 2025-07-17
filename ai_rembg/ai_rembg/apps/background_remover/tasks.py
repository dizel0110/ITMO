import logging
from datetime import timedelta
from io import BytesIO

from botocore.exceptions import IncompleteReadError
from constance import config
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from PIL import Image
from rembg import remove

from ai_photoenhancer.apps.background_remover.models import ImageInfo
from ai_photoenhancer.celeryapp import app
from ai_photoenhancer.utils.storage_tools import get_s3_client

logger = logging.getLogger(__name__)


@app.task(name='background_remover', ignore_results=True)
def remove_background(image_id: int) -> None:
    image_info = ImageInfo.objects.get(pk=image_id)
    client = get_s3_client()
    try:
        get_object_response = client.get_object(
            Bucket=config.STORAGE_NAME,
            Key=f'{config.EXAMPLES_PATH}{image_info.filename}',
        )
        photo_received = get_object_response['Body'].read()
    except client.exceptions.NoSuchKey:
        if timezone.now() - image_info.created_at > timedelta(seconds=settings.UPLOAD_LINK_LIFETIME):
            image_info.delete()
            logger.warning('Upload link expired, entry deleted')
        return
    except IncompleteReadError as err:
        logger.warning(err)
        return
    try:
        output = remove(Image.open(BytesIO(photo_received)))
        output.convert('RGB')
        result_obj = BytesIO()
        output.save(result_obj, 'PNG')
        result_obj.seek(0)
    except Exception as err:  # noqa: B902, pylint: disable=W0718
        logger.error(err)
        image_info.processed_at = timezone.now()
        image_info.errors = str(err)
        image_info.save()
        return
    client.put_object(
        Bucket=config.STORAGE_NAME,
        Key=f'{config.RESULTS_PATH}{image_info.filename}{config.RESULT_FILENAME_POSTFIX}.png',
        Body=result_obj,
    )
    image_info.processed_at = timezone.now()
    image_info.save()


@app.task(ignore_results=True)
def process_images() -> None:
    unprocessed_images = ImageInfo.objects.filter(
        processed_at__isnull=True,
    )
    for image_info in unprocessed_images:
        remove_background.delay(image_info.pk)


@app.task(ignore_results=True)
def clear_old_images() -> None:
    object_filter = Q(
        requested_at__isnull=False,
        requested_at__lt=timezone.now() - timedelta(hours=settings.RETURNED_IMAGES_STORE_TIME),
    )
    object_filter |= Q(
        processed_at__isnull=False,
        processed_at__lt=timezone.now() - timedelta(hours=settings.PROCESSED_IMAGES_STORE_TIME),
    )
    keys_to_delete = [
        {'Key': f'{config.RESULTS_PATH}{filename}{config.RESULT_FILENAME_POSTFIX}.png'}
        for filename in ImageInfo.objects.filter(object_filter).values_list('filename', flat=True)
    ]
    keys_to_delete.extend(
        [
            {'Key': f'{config.EXAMPLES_PATH}{filename}'}
            for filename in ImageInfo.objects.filter(object_filter).values_list('filename', flat=True)
        ],
    )

    client = get_s3_client()
    for batch_no in range(len(keys_to_delete) // 1000 + 1):  # max 1000 keys in one request (S3 limit)
        client.delete_objects(
            Bucket=config.STORAGE_NAME,
            Delete={
                'Objects': keys_to_delete[batch_no * 1000 : (batch_no + 1) * 1000],
                'Quiet': True,
            },
        )

    ImageInfo.objects.filter(object_filter).delete()
