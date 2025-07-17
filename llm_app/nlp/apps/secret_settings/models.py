from typing import Any

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _


class LLMSettings(models.Model):
    name = models.CharField(
        _('Name'),
        max_length=100,
        db_index=True,
        unique=True,
        default='feature extraction',
    )
    model = models.CharField(_('Model'), max_length=255)
    temperature = models.FloatField(_('Temperature'), default=0.0)
    top_p = models.FloatField(_('Top P'), default=0.99)
    max_tokens = models.IntegerField(_('Max Tokens'), default=3000)
    repetition_penalty = models.FloatField(_('Repetition Penalty'), default=1.0)
    seed = models.IntegerField(_('Seed'), default=0)

    class Meta:
        verbose_name = _('LLM setting')
        verbose_name_plural = _('LLM settings')

    def __str__(self) -> str:
        return f'{self.name}'


class Prompt(models.Model):
    name = models.CharField(
        _('Name'),
        max_length=100,
        db_index=True,
        unique=True,
    )
    system_text = models.TextField(_('System prompt'), blank=True)
    example_request_text = models.TextField(_('Example request prompt'), blank=True)
    example_answer_text = models.TextField(_('Example answer prompt'), blank=True)
    answer_format = models.TextField(_('Answer format'), blank=True)

    class Meta:
        verbose_name = _('Prompt')
        verbose_name_plural = _('Prompts')

    def __str__(self) -> str:
        return f'{self.name}'


class DBStructure(models.Model):
    name = models.CharField(
        _('Name'),
        max_length=100,
        db_index=True,
        unique=True,
        default='Descriptions',
    )
    structure = models.JSONField(_('Structure'))

    class Meta:
        verbose_name = _('DB setting')
        verbose_name_plural = _('DB settings')

    def __str__(self) -> str:
        return f'{self.name}'


class DBEntities(models.Model):
    name = models.CharField(_('Entity Name'), max_length=100, db_index=True, unique=True)
    entity_class = models.CharField(_('Class'), max_length=100)
    parents = ArrayField(models.IntegerField(), verbose_name=_('Parents'), default=list, blank=True, null=True)
    uploaded_to_pkl = models.BooleanField(_('Uploaded to pkl'), default=False)

    class Meta:
        verbose_name = _('Entity')
        verbose_name_plural = _('Entities')

    def __str__(self) -> str:
        return self.name


class GlobalProcessingSettings(models.Model):
    is_active = models.BooleanField(
        _('Is Active'),
        default=False,
        db_index=True,
        help_text=_('Indicates whether this setup is currently active.'),
    )
    shifted_window = models.BooleanField(_('Shifted Window'), default=True)
    unification = models.BooleanField(_('Unification'), default=True)
    rephrase = models.BooleanField(_('Rephrase'), default=True)

    class Meta:
        verbose_name = _('Global LLM Processing setting')
        verbose_name_plural = _('Global LLM Processing settings')

    def __str__(self) -> str:
        return f'Global Settings (Active: {self.is_active})'

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.is_active:
            GlobalProcessingSettings.objects.filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)
