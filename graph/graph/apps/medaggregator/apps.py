from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MedaggregatorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'akcent_graph.apps.medaggregator'
    verbose_name = _('Medcard Aggregator')
