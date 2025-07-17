from typing import Optional

from django.contrib import admin
from django.template.defaultfilters import truncatechars
from django.utils.translation import gettext_lazy as _

from nlp.apps.secret_settings.models import DBEntities, DBStructure, GlobalProcessingSettings, LLMSettings, Prompt


@admin.register(LLMSettings)
class LLMSettingsAdmin(admin.ModelAdmin):
    list_display = [
        'model',
        'temperature',
        'top_p',
        'max_tokens',
        'repetition_penalty',
        'seed',
    ]


@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'system_text',
        'example_request_text',
        'example_answer_text',
        'answer_format',
    ]


@admin.register(DBStructure)
class DBStructureAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'get_structure_display',
    ]

    @admin.display(description=_('Structure'))
    def get_structure_display(self, obj: DBStructure) -> Optional[str]:
        return truncatechars(str(obj.structure), 50)


@admin.register(GlobalProcessingSettings)
class GlobalProcessingSettingsAdmin(admin.ModelAdmin):
    list_display = [
        'is_active',
        'shifted_window',
        'unification',
        'rephrase',
    ]


@admin.register(DBEntities)
class DBEntitiesAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'entity_class',
        'parents',
    ]
