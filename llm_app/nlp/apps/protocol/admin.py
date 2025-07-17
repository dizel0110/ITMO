# pylint: disable=no-name-in-module
import json
from typing import Any

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest
from django.template.defaultfilters import truncatechars
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import JsonLexer

from nlp.apps.protocol.models import ParsingError, Protocol, ProtocolStructureError
from nlp.celeryapp import app
from nlp.utils.LLM.tasks import process_protocol_list


@admin.register(Protocol)
class ProtocolAdmin(admin.ModelAdmin):
    list_display = [
        'medcard_id',
        'user_id',
        'service_id',
        'processed_at',
        'is_sent_to_graphdb',
        'is_saved_to_graphdb',
    ]
    readonly_fields = ('pretty_protocol',)
    search_fields = ['user_id__exact', 'medcard_id__exact']
    search_help_text = _('Search by user ID or medcard ID')
    actions = ['priority_process_protocols']

    @admin.action(description=_('Priority process protocols'))
    def priority_process_protocols(self, request: HttpRequest, queryset: QuerySet[Protocol]) -> None:
        inspect = app.control.inspect()  # type: ignore[attr-defined]
        for __, queue_task_list in inspect.active().items():
            for active_task in queue_task_list:
                if active_task.get('name') == 'nlp.utils.LLM.tasks.process_protocols':
                    self.message_user(
                        request,
                        _('Main processing is running (task ID {})! Stop it first by the button below.').format(
                            active_task.get('id'),
                        ),
                        messages.ERROR,
                    )
                    return
        protocol_ids = list(queryset.values_list('pk', flat=True))
        process_protocol_list.apply_async((protocol_ids,), queue='low')

    def pretty_protocol(self, instance: Any) -> str:
        """Function to display pretty version of json data"""

        # Convert the data to sorted, indented JSON
        response = json.dumps(instance.result, sort_keys=True, indent=2, ensure_ascii=False)

        # Get the Pygments formatter
        formatter = HtmlFormatter(style='emacs')

        # Highlight the data
        response = highlight(response, JsonLexer(), formatter)

        # Get the stylesheet
        style = '<style>' + formatter.get_style_defs() + '</style><br>'

        # Safe the output
        return mark_safe(style + response)

    pretty_protocol.short_description = 'Readable'  # type: ignore[attr-defined]


@admin.register(ProtocolStructureError)
class ProtocolStructureErrorAdmin(admin.ModelAdmin):
    list_display = ['id', 'protocol_id', 'created_at']
    readonly_fields = ('created_at', 'pretty_errors')
    raw_id_fields = ['protocol']

    def pretty_errors(self, instance: Any) -> str:
        """Function to display pretty version of json data"""

        response = json.dumps(instance.errors, sort_keys=True, indent=2, ensure_ascii=False)
        formatter = HtmlFormatter(style='emacs')
        response = highlight(response, JsonLexer(), formatter)
        style = '<style>' + formatter.get_style_defs() + '</style><br>'
        return mark_safe(style + response)

    pretty_errors.short_description = 'Readable'  # type: ignore[attr-defined]


@admin.register(ParsingError)
class ParsingErrorAdmin(admin.ModelAdmin):
    list_display = ['id', 'protocol_id', 'error_type', 'get_message_display', 'processed_at']
    readonly_fields = ('processed_at',)
    actions = ['return_to_processing']
    raw_id_fields = ['protocol']

    @admin.action(description=_('Return protocols to autoprocessing'))
    def return_to_processing(self, request: HttpRequest, queryset: QuerySet[ParsingError]) -> None:
        Protocol.objects.filter(
            pk__in=queryset.values_list('protocol_id', flat=True),
            result__isnull=True,
        ).update(processed_at=None)

    @admin.display(description=_('Error message'))
    def get_message_display(self, obj: Any) -> str:
        return truncatechars(obj.error_message, 50)
