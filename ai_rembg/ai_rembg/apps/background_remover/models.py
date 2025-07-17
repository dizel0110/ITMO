from django.db import models
from django.utils.translation import gettext_lazy as _


class ImageInfo(models.Model):
    user_id = models.PositiveIntegerField(_('User ID'))
    filename = models.CharField(_('Filename'), max_length=50, editable=False)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True, editable=False)
    processed_at = models.DateTimeField(_('Processed at'), null=True, blank=True)
    requested_at = models.DateTimeField(_('Requested at'), null=True, blank=True)
    errors = models.TextField(_('Errors'), blank=True)

    class Meta:
        verbose_name = _('Image information')
        verbose_name_plural = _('Images information')

    def __str__(self) -> str:
        return f'{self.user_id}: {self.filename}'
