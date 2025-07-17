from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from model_utils import FieldTracker


class User(AbstractUser):
    created_at = models.DateTimeField(auto_now_add=True)
    tracker = FieldTracker()

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ('-created_at',)

        indexes = [
            models.Index(fields=['username'], name='username_idx'),
        ]

    def __str__(self) -> str:
        return self.first_name or self.username or _('Unknown user')  # type: ignore[return-value]
