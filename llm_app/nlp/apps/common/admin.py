from typing import Any

from constance.admin import Config, ConstanceAdmin
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import path

from .forms import CustomUserChangeForm
from .models import User
from .services.email import send_test_email_async


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm

    def get_readonly_fields(self, request: HttpRequest, obj: Any = None) -> list[str]:
        fields = list(super().get_readonly_fields(request))
        fields_to_block = [
            'is_staff',
            'groups',
            'is_superuser',
            'user_permissions',
            'is_banned_until',
        ]
        if not request.user.is_superuser:  # type: ignore[union-attr]
            for field in fields_to_block:
                fields.append(field)
        return fields

    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'is_superuser',
    )
    fieldsets = ((None, {'fields': ()}),) + BaseUserAdmin.fieldsets  # type: ignore

    save_on_top = True
    search_fields = ('username', 'first_name', 'last_name', 'email')


class ConfigAdmin(ConstanceAdmin):
    change_list_template = f'{settings.PROJECT_DIR}/templates/admin/send_test_email.html'

    def get_urls(self) -> list[Any]:
        urls = super().get_urls()
        custom_urls = [
            path('send_test_email/', self.send_test_email_view, name='send_test_email'),
        ]
        return custom_urls + urls

    @classmethod
    def send_test_email_view(cls, request: HttpRequest) -> HttpResponse:
        send_test_email_async()
        return redirect('admin:constance_config_changelist')


admin.site.unregister([Config])
admin.site.register([Config], ConfigAdmin)
