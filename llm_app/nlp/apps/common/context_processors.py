from typing import Any

from django.conf import settings
from django.http import HttpRequest


def akcent_settings(request: HttpRequest) -> dict[str, Any]:
    """Return context variables with printum settings."""
    return {
        'is_production': settings.ENV == 'production',
        'backend_prefix': settings.FORCE_SCRIPT_NAME,
        'global_cleaner_mode': settings.GLOBAL_CLEANER,
    }
