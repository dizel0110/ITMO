from typing import Any

from django.core.management.base import BaseCommand

from nlp.apps.common.models import User


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> str:
        if User.objects.filter(username='clinicadmin').exists():
            return 'Admin account already exists'
        user = User.objects.create_user('clinicadmin', password='admin825')  # type: ignore[attr-defined]
        user.is_superuser = False
        user.is_staff = True
        user.save()
        return 'Admin account created'
