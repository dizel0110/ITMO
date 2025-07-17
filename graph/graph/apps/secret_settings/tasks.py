import logging
import os

import requests
from django.conf import settings

from akcent_graph.celeryapp import app

logger = logging.getLogger(__name__)


@app.task(ignore_results=True)
def download_embeddings_from_s3() -> None:
    try:
        params = {'uid': settings.LICENSE_COMPANY_UID, 'name': 'entities'}
        response = requests.get(
            settings.LICENSE_SERVER_S3_DISPATCHER,
            params=params,
            timeout=settings.TIMEOUT_SHORT,
            stream=True,
        )
        response.raise_for_status()

        with open(os.path.join('private', 'pkls', 'entities.pkl'), 'wb') as file:
            for chunk in response.iter_content(chunk_size=1024):
                file.write(chunk)

    except requests.exceptions.RequestException as exc:
        logger.error('Error downloading file', exc_info=exc)
