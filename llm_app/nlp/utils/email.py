"""SMTP email backend class."""

import logging
from collections.abc import Mapping, Sequence
from typing import Any, Optional, Union

from constance import config
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.mail.backends.smtp import EmailBackend
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class ConstanceEmailBackend(EmailBackend):
    """A wrapper that manages the SMTP network connection with parameters set in Constance"""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: Optional[bool] = None,
        use_ssl: Optional[bool] = None,
        timeout: Optional[int] = None,
        ssl_keyfile: Optional[str] = None,
        ssl_certfile: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(
            host=host,
            port=port,
            username=username,
            password=password,
            use_tls=use_tls,
            use_ssl=use_ssl,
            timeout=timeout,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
            **kwargs,
        )
        self.host = host or config.EMAIL_HOST
        self.port = port or config.EMAIL_PORT
        self.username = username or config.EMAIL_HOST_USER
        self.password = password or config.EMAIL_HOST_PASSWORD
        self.use_tls = use_tls or config.EMAIL_USE_TLS
        self.use_ssl = use_ssl or config.EMAIL_USE_SSL
        self.timeout = timeout or settings.EMAIL_TIMEOUT
        self.ssl_keyfile = ssl_keyfile or settings.EMAIL_SSL_KEYFILE
        self.ssl_certfile = ssl_certfile or settings.EMAIL_SSL_CERTFILE


def send_email(
    subject: str,
    message: str,
    recipients: Optional[Sequence[str]] = None,
    attachments: Optional[Sequence[str]] = None,
    html_message: Optional[str] = None,
    reply_to: Union[tuple[Any], list[Any]] = (),  # type: ignore[assignment]
    from_email: Optional[str] = None,
) -> None:
    """Send email message with optional attachments.

    :param subject - Subject of email message.
    :param message - Message body of email message (plain text).
    :param recipients - Recipients emails (list of strings or string).
    :param attachments - List of tuple pairs (attachment filepath and its mimetype).
    :param html_message - Message body of email message (html).
    :param reply_to - list of addresses to reply to.
    :param from_email - email from address.
    """
    if isinstance(recipients, str):
        recipients = (recipients,)
    logger.debug(f'Send email to recipients: {recipients}')
    from_email = from_email or config.EMAIL_FROM
    msg = EmailMultiAlternatives(subject, message, from_email, recipients, reply_to=reply_to)

    if html_message is not None:
        msg.attach_alternative(html_message, 'text/html')

    if attachments is not None:
        for attachment in attachments:
            msg.attach_file(*attachment)

    msg.send()


def get_email_body(template_path: str, context: Optional[Mapping[str, Any]] = None) -> tuple[str, str]:
    """Render template as HTML and as a plain text for emails.

    :param template_path: path to a template
    :param context: context dict to build a template
    """
    html_content = render_to_string(template_path, context)
    text_content = strip_tags(html_content)
    return text_content, html_content
