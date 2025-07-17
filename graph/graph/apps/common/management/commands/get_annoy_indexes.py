import os
from typing import Any, Optional

from constance import config
from django.conf import settings
from django.core.management.base import BaseCommand

from akcent_graph.utils.clients.annoy_similary.save_annoy_indexes import SaveAnnoyIndexesPkl


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        saving_annoy = SaveAnnoyIndexesPkl()
        if not os.path.exists(settings.ANN_DATA_PATH):
            os.makedirs(settings.ANN_DATA_PATH)
        embedding_size = saving_annoy.save_indexes_pkl(
            settings.ICD_SYMPTOM_DATA,
            settings.ICD_SYMPTOM_DATA_ANN,
            100,
            'query',
        )
        config.ICD_SYMPTOM_SIZE = embedding_size

        return 'Saving annoy indexes completed'
