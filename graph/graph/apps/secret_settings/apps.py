from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SecretSettingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'akcent_graph.apps.secret_settings'
    verbose_name = _('Advanced Settings')
