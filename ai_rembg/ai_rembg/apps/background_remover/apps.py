from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class BackgroundRemoverConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ai_photoenhancer.apps.background_remover'
    verbose_name = _('Background remover settings')

    def ready(self) -> None:
        import ai_photoenhancer.apps.background_remover.signals  # noqa
