import logging
import time

import requests
from django.conf import settings
from django.core.cache import cache

from nlp.apps.common.ext_webservice_adapters import GraphDBAdapter
from nlp.apps.common.ext_webservice_auth import get_ext_webservice_token
from nlp.apps.protocol.models import Protocol
from nlp.apps.protocol.serializers import ProtocolGraphDBSerializer
from nlp.celeryapp import app

logger = logging.getLogger(__name__)


@app.task(ignore_results=True)
def send_protocols_to_graphdb() -> None:
    neuro_graphdb_data_structure_ok = cache.get('neuro_graphdb_data_structure_ok')
    if neuro_graphdb_data_structure_ok is None:
        check_neuro_graphdb_data_structure_concordance.apply_async(queue='low')
        return
    if not neuro_graphdb_data_structure_ok:
        logger.error('Neuro-GraphDB data structure does not match. Check immediately!')
        return
    if not Protocol.objects.filter(
        result__isnull=False,
        is_sent_to_graphdb=False,
    ).exists():
        logger.info('No protocols to send')
        return
    adapter = GraphDBAdapter()
    if not adapter.is_ready:
        logger.warning('Connection adapter not ready!')
        return
    while True:
        protocols = Protocol.objects.filter(
            result__isnull=False,
            is_sent_to_graphdb=False,
        )[:300]
        if not protocols:
            logger.info('No more protocols to send')
            return
        protocol_ids = [protocol.pk for protocol in protocols]
        Protocol.objects.filter(pk__in=protocol_ids).update(is_sent_to_graphdb=True)
        for number, protocol in enumerate(protocols):
            try:
                adapter.post_protocol(protocol)
            except requests.exceptions.RequestException as err:
                logger.error('Error sending protocols to GraphDB', exc_info=err)
                Protocol.objects.filter(pk__in=protocol_ids[number:]).update(is_sent_to_graphdb=False)
                return


@app.task(ignore_results=True)
def check_neuro_graphdb_data_structure_concordance() -> None:
    protocol = Protocol(
        medcard_id='2c1247ba-a17b-470b-aa4e-01e707154120',
        user_id='2c1247ba-a17b-470b-aa4e-01e707154120',
        protocol_custom_id='2c1247ba-a17b-470b-aa4e-01e707154120',
        service_id=1234567,
        result=[
            {
                'name': '269a0e7a-82b1-4cd0-9013-8098f9cbd4c0',  # test protocol marker, do not change this!!!
                'class': 'NeoMedServiceFeature',
                'index': 1,
                'value': None,
                'parents': [],
                'index_bd': None,
            },
        ],
    )
    sent_data = ProtocolGraphDBSerializer(protocol).data
    adapter = GraphDBAdapter()
    if not adapter.is_ready:
        return
    try:
        adapter.post_protocol(protocol)
    except ValueError:
        cache.set('neuro_graphdb_data_structure_ok', False, timeout=settings.DATA_STRUCTURE_CHECK_TIMEOUT)
        logger.error('Neuro-GraphDB data structure does not match. Check immediately!')
        return
    time.sleep(5)
    token = get_ext_webservice_token()
    response = requests.get(
        f'{settings.GRAPHDB_PROTOCOL_BACKEND}/medaggregator/protocol/2c1247ba-a17b-470b-aa4e-01e707154120/',
        headers={'Authorization': f'Bearer {token}'},
        timeout=settings.TIMEOUT_SHORT,
    )
    response.raise_for_status()
    if response.json() == sent_data:
        cache.set('neuro_graphdb_data_structure_ok', True, timeout=settings.DATA_STRUCTURE_CHECK_TIMEOUT)
        logger.info('Neuro-GraphDB data structure matches!')
    else:
        cache.set('neuro_graphdb_data_structure_ok', False, timeout=settings.DATA_STRUCTURE_CHECK_TIMEOUT)
        logger.error('Neuro-GraphDB data structure does not match. Check immediately!')
