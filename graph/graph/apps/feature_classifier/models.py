from ast import literal_eval
from typing import Any

from constance import config
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from akcent_graph.utils.processing_medical_records import ProcessingMedicalRecords


class FeatureClassifier(models.Model):
    feature = models.TextField(_('Features'))
    importance = models.TextField(_('Importance'), blank=True)
    annoy_score = models.TextField(_('Annoy scores'), blank=True)
    gpt_description = models.TextField(_('GPT description'), blank=True)

    class Meta:
        verbose_name = _('Feature Classifier')
        verbose_name_plural = _('Features Classifier')

    def __str__(self) -> str:
        return f'{self.feature}'

    def save(self, *args: Any, **kwargs: Any) -> None:
        # TODO need refactoring this function
        list_features = literal_eval(self.feature)
        recorder = ProcessingMedicalRecords(
            data_path_ann=settings.ICD_SYMPTOM_DATA_ANN,
            size_ann=config.ICD_SYMPTOM_SIZE,
            metric_ann=config.ICD_SYMPTOM_METRIC,
        )

        answer_marker = ''
        answer_annoy_score = ''
        answer_description = ''
        for feature in list_features:
            marker, annoy_score, description = recorder.determining_feature_importance(
                feature['имя'],
                feature['значение'],
            )
            answer_marker += f'Название фичи: {feature["имя"]}. Её важность: {marker}\n'
            answer_annoy_score += (
                f'Название фичи: {feature["имя"]}. Оценка анноя из пикла (индекс из пикла и оценка): {annoy_score}\n'
            )
            answer_description += f'Название фичи: {feature["имя"]}. Описание: {description}\n'

        self.importance = answer_marker
        self.annoy_score = answer_annoy_score
        self.gpt_description = answer_description
        super().save(*args, **kwargs)


class AdditionalFeatureClassifier(models.Model):
    feature = models.TextField(_('Features'))
    additional_feature = models.TextField(_('Additional features'), blank=True)
    importance = models.TextField(_('Importance'), blank=True)
    annoy_score = models.TextField(_('Annoy scores'), blank=True)
    gpt_description = models.TextField(_('GPT description'), blank=True)

    class Meta:
        verbose_name = _('Additional feature Classifier')
        verbose_name_plural = _('Additional features Classifier')

    def __str__(self) -> str:
        return f'{self.feature}: {self.additional_feature}'

    def save(self, *args: Any, **kwargs: Any) -> None:
        # TODO need refactoring this function
        feature = literal_eval(self.feature)
        if self.additional_feature:
            additional_feature = literal_eval(self.additional_feature)
        else:
            additional_feature = None
        recorder = ProcessingMedicalRecords(
            settings.MERGE_ICD_SYMPTOM_DATA,
        )

        marker, annoy_score, description = recorder.determining_importance_with_additional_feature(
            feature,
            additional_feature,
        )

        self.importance = str(marker)
        self.annoy_score = str(annoy_score)
        self.gpt_description = description
        super().save(*args, **kwargs)


class DescriptionFeature(models.Model):
    name = models.TextField(_('Name'), blank=True)
    value = models.TextField(_('Value'))
    gpt_description = models.TextField(_('GPT description'))

    class Meta:
        verbose_name = _('Feature description Classifier')
        verbose_name_plural = _('Feature descriptions Classifier')
        unique_together = ('name', 'value')

    def __str__(self) -> str:
        return f'{self.name}: {self.value}'


class AbbreviatedPhrase(models.Model):
    abbreviated_phrase = models.TextField(_('Abbreviated phrase'), unique=True)
    decrypted_phrase = models.TextField(_('Decrypted phrase'))

    class Meta:
        verbose_name = _('Abbreviated phrase')
        verbose_name_plural = _('Abbreviated phrases')

    def __str__(self) -> str:
        return f'{self.abbreviated_phrase}'
