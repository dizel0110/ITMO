from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class FeatureClassifierConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'akcent_graph.apps.feature_classifier'
    verbose_name = _('Features classifier')
