from functools import cache as fcache
from typing import Any

import boto3
from constance import config
from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class StorageType(TextChoices):
    S3 = 's3', _('S3 storage')

    __empty__ = '-----'


@fcache
def get_s3_client() -> Any:
    session = boto3.Session(
        aws_access_key_id=config.STORAGE_LOGIN,
        aws_secret_access_key=config.STORAGE_PASSWORD,
        region_name=config.STORAGE_LOCATION,
    )
    return session.client(
        service_name=config.STORAGE_TYPE,
        endpoint_url=config.STORAGE_HOST,
    )
