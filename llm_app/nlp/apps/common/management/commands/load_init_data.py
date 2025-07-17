from typing import Any

from django.core.management import call_command
from django.core.management.base import BaseCommand

from nlp.apps.secret_settings.models import Prompt


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> None:
        if not Prompt.objects.exists():
            call_command('loaddata', 'db_init/secret_settings.json')
            self.stdout.write(self.style.SUCCESS('Initial data loaded in database'))
