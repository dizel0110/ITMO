from typing import Any, Optional

from django.core.management import call_command
from django.core.management.base import BaseCommand

from akcent_graph.apps.medaggregator.models import Speciality
from akcent_graph.apps.secret_settings.models import Prompt
from akcent_graph.utils.clients.gpt.tasks import update_quotes_gpt


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        Prompt.objects.all().delete()
        call_command('loaddata', 'db_init/secret_settings.json')

        update_quotes_gpt()

        if not Speciality.objects.exists():
            call_command('loaddata', 'db_init/speciality.json')

        return 'Initial data loaded in database'
