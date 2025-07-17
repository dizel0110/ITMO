import logging
from typing import Any

from django.core.management.color import Style, color_style


def configure_style(style: Any) -> Style:
    style.DEBUG = style.HTTP_NOT_MODIFIED
    style.INFO = style.HTTP_INFO
    style.WARNING = style.HTTP_NOT_FOUND
    style.ERROR = style.ERROR
    style.CRITICAL = style.HTTP_SERVER_ERROR
    return style


class DjangoColorsFormatter(logging.Formatter):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.style = configure_style(color_style())

    def format(self, record: logging.LogRecord) -> str:
        message = logging.Formatter.format(self, record)
        colorizer = getattr(self.style, record.levelname, self.style.HTTP_SUCCESS)
        return colorizer(message)
