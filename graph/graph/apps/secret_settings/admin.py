from django.contrib import admin

from .models import GigaChatSettings, Prompt, YGPTSettings


@admin.register(YGPTSettings)
class YGPTSettingsAdmin(admin.ModelAdmin):
    role_full_permissions = ['can_edit_ygpt_settings']
    role_view_permissions = ['can_view_ygpt_settings']

    list_display = [
        'api_key',
        'folder_id',
        'headers',
        'url_operation_result_prefix',
        'text_embedding_url',
        'completion_sync_url',
        'completion_async_url',
        'request_timeout',
        'simultaneous_generations',
        'sync_quota_per_hour',
        'async_quota_per_hour',
    ]


@admin.register(GigaChatSettings)
class GigaChatSettingsAdmin(admin.ModelAdmin):
    role_full_permissions = ['can_edit_gigachat_settings']
    role_view_permissions = ['can_view_gigachat_settings']

    list_display = [
        'api_key',
        'auth_headers',
        'req_headers_keyword',
        'auth_url',
        'text_embedding_url',
        'completion_url',
        'request_timeout',
        'queue_timeout',
        'response_timeout',
        'simultaneous_generations',
        'quota_per_hour',
    ]


@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    role_full_permissions = ['can_edit_ygpt_settings']
    role_view_permissions = ['can_view_ygpt_settings']

    list_display = [
        'name',
        'user_text',
        'system_text',
    ]
