import logging
from typing import Any, Mapping, Optional

from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

MESSAGE_TYPES = {
    'test_message': {
        'subject': _('[Akcent] Test Email'),
        'template': 'emails/test_email.html',
    },
}


def get_subject(message_type: str) -> Optional[str]:
    return MESSAGE_TYPES.get(message_type, {}).get('subject')  # type: ignore[return-value]


def get_template(message_type: str) -> Optional[str]:
    return MESSAGE_TYPES.get(message_type, {}).get('template')  # type: ignore[return-value]


def get_template_as_string(message_type: str, context: Mapping[str, Any], plain: bool = False) -> str:
    """
    Function finds template, representing message for specified status code and
    returns it as a string, with html tags or not.

    :param message_type - Type of message to send.
    :param context - Context dict to build template.
    :param plain - Type of message to return. Html by default.
    """
    template_path = get_template(message_type)
    template = render_to_string(template_path, context)  # type: ignore[arg-type]
    if plain:
        template = strip_tags(template)  # type: ignore[assignment]
    return template


def get_message(message_type: str, context: Mapping[str, Any]) -> tuple[str | None, str, str]:
    """
    Render template for specified message type and return
    its email message subject, text/plain and html versions.

    :param message_type - Type of message to send.
    :param context - Context dict to build template.
    """
    text_content = get_template_as_string(message_type, context, plain=True)
    html_content = get_template_as_string(message_type, context)
    subject = get_subject(message_type)
    return subject, text_content, html_content
