from typing import Any, Optional

from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from model_utils import FieldTracker


class CustomUserManager(UserManager):  # type: ignore[type-arg]
    def create_superuser(
        self,
        username: str,
        email: Optional[str] = None,
        password: Optional[str] = None,
        **extra_fields: Any,
    ) -> None:
        raise ValidationError('Superuser creation not permitted')

    def create_akcent_superadmin(
        self,
        username: str,
        email: Optional[str] = None,
        password: Optional[str] = None,
        **extra_fields: Any,
    ) -> Any:
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    created_at = models.DateTimeField(auto_now_add=True)  # type: ignore[var-annotated]

    objects = CustomUserManager()

    tracker = FieldTracker()

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ('-created_at',)

        indexes = [
            models.Index(fields=['username'], name='username_idx'),
        ]

    def __str__(self) -> Any:
        return ' '.join((self.last_name, self.first_name)).strip() or self.username or _('Unknown user')
