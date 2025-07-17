import json
from datetime import datetime, timedelta
from typing import Any

from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from pygments import highlight
from pygments.formatters import HtmlFormatter  # pylint: disable=no-name-in-module
from pygments.lexers import JsonLexer  # pylint: disable=no-name-in-module
from rangefilter.filters import DateTimeRangeFilterBuilder

from akcent_graph.apps.medaggregator.models import (
    Diagnosis,
    PatientDigitalParam,
    PatientMedcard,
    PatientStringParam,
    Protocol,
)
from akcent_graph.apps.medaggregator.serializers import DiagnosisSerializer


@admin.register(Protocol)
class ProtocolAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'protocol_custom_id',
        'loaded_to_graphdb_at',
        'classified_at',
        'unmarked_features_left',
        'attentions_changed',
        'marked_with_errors',
    ]
    readonly_fields = ['created_at']
    search_fields = [
        'protocol_custom_id__exact',
        'patient_medcard__user_id__exact',
        'patient_medcard__medcard_id__exact',
        'id',
        'logging_from_marked',
    ]
    search_help_text = _('Search by protocol custom ID or user ID or medcard ID or pk protocol or logging')
    raw_id_fields = ['patient_medcard']

    list_filter = (
        'unmarked_features_left',
        'attentions_changed',
        'marked_with_errors',
        (
            'loaded_to_graphdb_at',
            DateTimeRangeFilterBuilder(
                title=_('Filter protocols by loading in graphdb'),
                default_start=datetime.now() - timedelta(days=1),
                default_end=datetime.now(),
            ),
        ),
        (
            'classified_at',
            DateTimeRangeFilterBuilder(
                title=_('Filter protocols by features classifier'),
                default_start=datetime.now() - timedelta(days=1),
                default_end=datetime.now(),
            ),
        ),
    )


@admin.register(PatientMedcard)
class PatientMedcardAdmin(admin.ModelAdmin):
    list_display = ['id', 'medcard_id', 'user_id', 'created_at', 'reprocessed_at', 'additional_marked_with_errors']
    readonly_fields = ['created_at', 'show_anamnesis']
    search_fields = ['medcard_id__exact', 'user_id__exact', 'id__exact', 'logging_from_marked']
    search_help_text = _('Search by user ID or medcard ID or patient medcard pk or logging')
    list_filter = (
        'additional_marked_with_errors',
        (
            'reprocessed_at',
            DateTimeRangeFilterBuilder(
                title=_('Filter patient medcard by reprocessed'),
                default_start=datetime.now() - timedelta(days=1),
                default_end=datetime.now(),
            ),
        ),
    )

    def show_anamnesis(self, instance: Any) -> str:
        diagnoses = Diagnosis.objects.filter(patient_medcard=instance).prefetch_related(
            'string_params',
            'digital_params',
        )
        serializer = DiagnosisSerializer(diagnoses, many=True)
        anamnesis: dict = {'diagnoses': []}
        for diagnosis in serializer.data:
            if string_params := diagnosis.pop('string_params', None):
                diagnosis['string_params'] = {}
                for param in string_params:
                    diagnosis['string_params'].setdefault(param.pop('group_id'), []).append(param)
            if digital_params := diagnosis.pop('digital_params', None):
                diagnosis['digital_params'] = {}
                for param in digital_params:
                    diagnosis['digital_params'].setdefault(param.pop('group_id'), []).append(param)
            anamnesis['diagnoses'].append(diagnosis)

        response = json.dumps(anamnesis, sort_keys=False, indent=2, ensure_ascii=False)
        formatter = HtmlFormatter(style='emacs')
        response = highlight(response, JsonLexer(), formatter)
        style = '<style>' + formatter.get_style_defs() + '</style><br>'
        return mark_safe(style + response)

    show_anamnesis.short_description = 'Anamnesis'  # type: ignore[attr-defined]


@admin.register(Diagnosis)
class DiagnosisAdmin(admin.ModelAdmin):
    list_display = ['id', 'patient_medcard', 'date_created']
    readonly_fields = ['date_created']
    raw_id_fields = ['patient_medcard', 'protocols']


@admin.register(PatientStringParam)
class PatientStringParamAdmin(admin.ModelAdmin):
    raw_id_fields = ['diagnosis', 'protocol']


@admin.register(PatientDigitalParam)
class PatientDigitalParamAdmin(admin.ModelAdmin):
    raw_id_fields = ['diagnosis', 'protocol']
