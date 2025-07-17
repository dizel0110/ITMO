from django.db.models import IntegerChoices
from django.utils.translation import gettext_lazy as _


class DiagnosisType(IntegerChoices):
    TEMPORARY = 0, _('Temporary')
    CHRONIC = 1, _('Chronic')

    __empty__ = _('(Undefined)')
