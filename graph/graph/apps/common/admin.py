from collections.abc import Sequence
from typing import Any, Optional, Union

from constance.admin import Config, ConstanceAdmin
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.http import HttpRequest

from .forms import CustomUserChangeForm
from .models import User


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm

    def get_readonly_fields(self, request: Union[HttpRequest, HttpRequest], obj: Optional[Any] = None) -> Sequence[str]:
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
    fieldsets = ((None, {'fields': ()}),) + BaseUserAdmin.fieldsets  # type: ignore[assignment, operator]

    save_on_top = True
    search_fields = ('username', 'first_name', 'last_name', 'email')


class ConfigAdmin(ConstanceAdmin):
    change_list_template = f'{settings.PROJECT_DIR}/templates/admin/custom_constance.html'


admin.site.unregister([Config])
admin.site.register([Config], ConfigAdmin)
