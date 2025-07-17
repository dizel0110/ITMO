from django.db import models
from django.utils.translation import gettext_lazy as _


class YGPTSettings(models.Model):
    api_key = models.TextField(_('API key'), blank=True)
    folder_id = models.TextField(_('Folder ID'), blank=True)
    headers = models.TextField(_('Headers'), blank=True)
    url_operation_result_prefix = models.TextField(_('URL operation result prefix'), blank=True)
    text_embedding_url = models.TextField(_('Text embedding url'), blank=True)
    completion_sync_url = models.TextField(_('Completion sync url'), blank=True)
    completion_async_url = models.TextField(_('Completion async url'), blank=True)
    request_timeout = models.FloatField(_('Request timeout'), default=10)
    sync_queue_timeout = models.FloatField(_('Synchron queue timeout'), default=10)
    response_timeout_async = models.FloatField(_('Response timeout async'), default=20)
    simultaneous_generations = models.IntegerField(_('Simultaneous generations'), default=10)
    sync_quota_per_hour = models.IntegerField(_('Synchronous quota per hour'), default=100)
    async_quota_per_hour = models.IntegerField(_('Asynchronous quota per hour'), default=5000)

    class Meta:
        verbose_name = _('YGPT url')
        verbose_name_plural = _('YGPT urls settings')

    def __str__(self) -> str:
        return (
            f'{self.api_key}\n'
            f'{self.folder_id}\n'
            f'{self.headers=}\n'
            f'{self.url_operation_result_prefix=}\n'
            f'{self.text_embedding_url=}\n'
            f'{self.completion_sync_url=}\n'
            f'{self.completion_async_url=}\n'
            f'{self.request_timeout=}\n'
        )


class GigaChatSettings(models.Model):
    api_key = models.TextField(_('API key'), blank=True)
    auth_headers = models.TextField(_('Authorization Header'), blank=True)
    req_headers_keyword = models.TextField(_('Request Header keyword'), blank=True)
    auth_url = models.TextField(_('Authorization url'), blank=True)
    text_embedding_url = models.TextField(_('Text embedding url'), blank=True)
    completion_url = models.TextField(_('Completion url'), blank=True)
    request_timeout = models.FloatField(_('Request timeout'), blank=True, null=True)
    queue_timeout = models.FloatField(_('Queue timeout'), blank=True, null=True)
    response_timeout = models.FloatField(_('Response timeout'), blank=True, null=True)
    simultaneous_generations = models.IntegerField(_('Simultaneous generations'), default=10)
    quota_per_hour = models.IntegerField(_('Quota per hour'), blank=True, null=True)

    class Meta:
        verbose_name = _('GigaChat url')
        verbose_name_plural = _('GigaChat urls settings')

    def __str__(self) -> str:
        return (
            f'{self.api_key}\n'
            f'{self.auth_headers=}\n'
            f'{self.req_headers_keyword=}\n'
            f'{self.auth_url=}\n'
            f'{self.text_embedding_url=}\n'
            f'{self.completion_url=}\n'
            f'{self.request_timeout=}\n'
        )


class Prompt(models.Model):
    name = models.CharField(
        _('Name'),
        max_length=100,
        db_index=True,
        unique=True,
    )
    user_text = models.TextField(_('User prompt'), blank=True)
    system_text = models.TextField(_('System prompt'), blank=True)

    class Meta:
        verbose_name = _('Prompt')
        verbose_name_plural = _('Prompts')

    def __str__(self) -> str:
        return f'{self.name}'
