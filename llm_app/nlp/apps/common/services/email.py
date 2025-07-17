import logging

from constance import config as admin_config

from .messages import get_message
from .tasks import send_email

logger = logging.getLogger(__name__)


def send_test_email_async() -> dict[str, str]:
    recipient = admin_config.EMAIL_SUPPORT
    attachments = None
    subject, text_message, html_message = get_message('test_message', {})
    send_email.apply_async((subject, text_message, recipient, attachments, html_message))
    return {'msg': 'Sent'}
