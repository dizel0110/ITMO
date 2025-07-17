from typing import Any, Optional

from constance import settings
from constance.backends.database import DatabaseBackend as BaseDatabaseBackend
from django.db import ProgrammingError


class DatabaseBackend(BaseDatabaseBackend):
    def get(self, key: Any) -> Optional[Any]:  # noqa C901
        key = self.add_prefix(key)
        if self._cache:
            value = self._cache.get(key)
            if value is None:
                self.autofill()
                value = self._cache.get(key)
        else:
            value = None
        if value is None:
            try:
                value = self._model._default_manager.get(key=key).value
            except self._model.DoesNotExist:
                pass
            except ProgrammingError as e:
                if e.args[0].split('\n')[0] == "relation 'constance_config' does not exist":
                    return settings.CONFIG[key][0]
                raise
            else:
                if self._cache:
                    self._cache.add(key, value)
        return value
