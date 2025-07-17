import logging
from typing import Optional

from constance import config
from django.core.mail import EmailMultiAlternatives

from nlp.celeryapp import app

logger = logging.getLogger(__name__)


@app.task
def send_email(
    subject: str,
    message: str,
    recipients: str | list[str],
    attachments: Optional[list[tuple[str, str]]] = None,
    html_message: Optional[str] = None,
    data_attachment: bool = False,
) -> bool:
    """
    Send email message with optional attachments.

    :param subject - Subject of email message.
    :param message - Message body of email message (plain text).
    :param recipients - Recipients emails (list of strings or string).
    :param attachments - List of tuple pairs (attachment filepath and its mimetype).
    :data_attachment - Attachment is a data. Not a file
    """
    if not isinstance(recipients, list):
        recipients = [recipients]
    logger.debug(f'Send email to users: {recipients}')
    msg = EmailMultiAlternatives(subject, message, config.EMAIL_HOST_USER, recipients)
    if html_message is not None:
        msg.attach_alternative(html_message, 'text/html')
    if attachments is not None:
        if data_attachment:
            for attachment in attachments:
                msg.attach(*attachment)
        else:
            for attachment in attachments:
                msg.attach_file(*attachment)

    try:
        msg.send()
        logger.debug('Email message sent.')
        return True
    except:  # noqa
        logger.debug('Email message not sent.')
        return False
