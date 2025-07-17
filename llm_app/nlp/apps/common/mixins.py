from typing import Any


class AllowAllStaffMixin:
    """Allows access to ModelAdmin and InlineModelAdmin for all is_staff users."""

    def has_module_permission(self, *args: Any, **kwargs: Any) -> bool:
        return True

    def has_view_permission(self, *args: Any, **kwargs: Any) -> bool:
        return True

    def has_add_permission(self, *args: Any, **kwargs: Any) -> bool:
        return True

    def has_change_permission(self, *args: Any, **kwargs: Any) -> bool:
        return True

    def has_delete_permission(self, *args: Any, **kwargs: Any) -> bool:
        return True
