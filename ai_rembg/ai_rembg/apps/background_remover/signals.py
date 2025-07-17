from typing import Any

from constance.signals import config_updated
from django.dispatch import receiver

from ai_photoenhancer.utils.storage_tools import get_s3_client


@receiver(config_updated)
def constance_updated(sender: Any, key: str, old_value: str, new_value: str, **kwargs: Any) -> None:
    get_s3_client.cache_clear()
