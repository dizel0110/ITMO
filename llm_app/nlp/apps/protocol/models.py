from django.db import models
from django.utils.translation import gettext_lazy as _


class Protocol(models.Model):
    medcard_id = models.CharField(_('Medcard ID'), max_length=50, blank=True)
    user_id = models.CharField(_('User ID'), max_length=50, blank=True)
    protocol_custom_id = models.CharField(
        _('Protocol Custom ID'),
        max_length=50,
        blank=True,
        help_text=_('User-defined arbitrary string. Do not edit manually!'),
    )
    service_id = models.IntegerField(_('Service ID'), null=True, blank=True)
    raw_text = models.TextField(_('Raw Text'))
    result = models.JSONField(_('Result'), null=True, blank=True)
    processed_at = models.DateTimeField(_('Processed at'), null=True, blank=True)
    parsing_error_count = models.IntegerField(_('Parsing errors count'), default=0)
    api_error_count = models.IntegerField(_('API errors count'), default=0)
    is_sent_to_graphdb = models.BooleanField(_('Is sent to GraphDB'), default=False)
    is_saved_to_graphdb = models.BooleanField(_('Is saved to GraphDB'), default=False)

    class Meta:
        verbose_name = _('Protocol')
        verbose_name_plural = _('Protocols')
        ordering = ['-processed_at']

    def __str__(self) -> str:
        return f'{self.user_id}: {self.medcard_id}'


class ProtocolStructureError(models.Model):
    protocol = models.ForeignKey(
        Protocol,
        on_delete=models.CASCADE,
        verbose_name=_('Protocol'),
        related_name='structure_errors',
    )
    errors = models.JSONField(_('Errors'), null=True, blank=True)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('Protocol structure error')
        verbose_name_plural = _('Protocol structure errors')
        ordering = ['-pk']

    def __str__(self) -> str:
        return f'{self.protocol_id}: {self.created_at}'


class ParsingError(models.Model):
    protocol = models.ForeignKey(
        Protocol,
        on_delete=models.CASCADE,
        verbose_name=_('Protocol'),
        related_name='parsing_errors',
    )
    error_type = models.CharField(_('Error type'), max_length=50, blank=True)
    traceback = models.TextField(_('Traceback'), blank=True)
    error_message = models.TextField(_('Error message'), blank=True)
    llm_response = models.JSONField(_('LLM response'), null=True, blank=True)
    processed_at = models.DateTimeField(_('Processed at'), auto_now_add=True)

    class Meta:
        verbose_name = _('Parsing error')
        verbose_name_plural = _('Parsing errors')
        ordering = ['-pk']

    def __str__(self) -> str:
        return f'{self.protocol_id}: {self.processed_at}'
