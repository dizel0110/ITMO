import asyncio
import logging
from functools import cache as ft_cache
from typing import Any, Optional

from asgiref.sync import sync_to_async
from celery.exceptions import Ignore
from constance import config
from django.db import connections
from django.db.models import Exists, OuterRef
from django.db.utils import InterfaceError, OperationalError
from django.utils import timezone

from akcent_graph.apps.common.tools import get_running_task_count
from akcent_graph.apps.feature_classifier.async_marking_features_protocols import AsyncMarkingProtocol
from akcent_graph.apps.feature_classifier.marking_features_protocols import MarkingProtocol
from akcent_graph.apps.medaggregator.models import NeoProtocol, PatientMedcard, Protocol
from akcent_graph.celeryapp import app

logger = logging.getLogger(__name__)


@sync_to_async
def reconnect_db() -> None:
    for conn_name in connections:
        conn = connections[conn_name]
        logger.info('Connection found: %s', conn_name)
        if conn.connection:
            logger.info('connection closed: %s', conn.connection.closed)
            logger.info('connection broken: %s', conn.connection.broken)

    conn = connections['default']
    if conn.connection:
        logger.warning('DB connection closed: %s', conn.connection.closed)
    logger.warning('Reconnecting to DB..')

    conn.close()
    conn.connection = None
    conn.connect()

    if conn.connection:
        logger.warning('DB connection closed: %s', conn.connection.closed)


@ft_cache
def get_extractor() -> AsyncMarkingProtocol:
    return AsyncMarkingProtocol()


@app.task(ignore_results=True)
def additional_marking_protocols() -> None:
    patients_unmarked = PatientMedcard.objects.filter(protocols__unmarked_features_left=True)
    patients = patients_unmarked.annotate(
        has_greater_child=Exists(
            Protocol.objects.filter(
                patient_medcard=OuterRef('pk'),
                classified_at__gt=OuterRef('reprocessed_at'),
            ),
        ),
    ).filter(has_greater_child=True) | patients_unmarked.filter(reprocessed_at__isnull=True)
    distinct_patients = patients.distinct()

    if distinct_patients:
        marking = MarkingProtocol(
            single_features_pkl=False,
        )
        for patient in distinct_patients:
            is_error, logging_from_marked = marking.additional_marking(
                patient.pk,
                patient.additional_marked_with_errors,
                patient.logging_from_marked,
            )
            patient.reprocessed_at = timezone.now()
            patient.additional_marked_with_errors = is_error
            patient.logging_from_marked = logging_from_marked
            patient.save()


@app.task(bind=True, ignore_results=True)
def marking_new_protocols(self: Any) -> None:
    # check if another instance of this task is running:
    if get_running_task_count(self.name) >= 2:
        logger.info('Another instance of this task is running. Cancelling current task...')
        raise Ignore()

    if not Protocol.objects.filter(
        classified_at__isnull=True,
        loaded_to_graphdb_at__isnull=False,
    ).exists():
        logger.info('No protocols to process. Exiting...')
        return
    extractor = get_extractor()
    batch = config.MARK_PROTOCOLS_BATCH
    asyncio.run(run_process_protocol(extractor, batch))


async def run_process_protocol(extractor: AsyncMarkingProtocol, batch: int = 1) -> None:
    protocol_queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=batch)
    await asyncio.gather(
        *[process_protocol(extractor, protocol_queue) for __ in range(batch)],
        take_protocol(batch, protocol_queue),
    )


@sync_to_async
def get_priority_users() -> list[str]:
    return config.PRIORITY_USERS.split()


@sync_to_async
def get_neo_protocol(protocol: Protocol) -> Optional[NeoProtocol]:
    return NeoProtocol.nodes.filter(  # pylint: disable=no-member
        name=protocol.pk,
        patient_id=protocol.patient_medcard.pk,
    ).first()


async def take_protocol(batch: int, protocol_queue: asyncio.Queue[Any]) -> Any:
    last_protocols: list[int] = []
    while True:
        try:
            priority_users = await get_priority_users()
            protocol = None
            if priority_users:
                protocol = (
                    await Protocol.objects.filter(
                        classified_at__isnull=True,
                        loaded_to_graphdb_at__isnull=False,
                        patient_medcard__user_id__in=priority_users,
                    )
                    .exclude(pk__in=last_protocols)
                    .afirst()
                )
            if not protocol:
                protocol = (
                    await Protocol.objects.filter(
                        classified_at__isnull=True,
                        loaded_to_graphdb_at__isnull=False,
                    )
                    .exclude(pk__in=last_protocols)
                    .afirst()
                )
        except (OperationalError, InterfaceError) as exc:
            logger.error('DB connection lost... ', exc_info=exc)
            await reconnect_db()
            continue

        if not protocol:
            logger.info('There are no more protocols...')
            for __ in range(batch):
                await protocol_queue.put(None)
            break

        last_protocols.insert(0, protocol.pk)
        last_protocols = last_protocols[:batch]

        await protocol_queue.put(protocol)


async def process_protocol(extractor: AsyncMarkingProtocol, protocol_queue: asyncio.Queue[Any]) -> None:
    while protocol := await protocol_queue.get():
        logger.info('Processing protocol id=%s', protocol.pk)
        try:
            protocol.classified_at = timezone.now()
            asyncio.ensure_future(protocol.asave())
            neo_protocol = await get_neo_protocol(protocol)

            if not neo_protocol:
                logger.warning(
                    'NeoProtocol does not exist with name: %s and patient_id: %s',
                    protocol.pk,
                    protocol.patient_medcard.pk,
                )
                protocol.classified_at = None
                protocol.loaded_to_graphdb_at = None
                asyncio.ensure_future(protocol.asave())
                continue

            markers, is_error, logging_from_marked = await extractor.marking_new_protocol(neo_protocol)
            protocol.classified_at = timezone.now()
            protocol.unmarked_features_left = None in markers
            protocol.attentions_changed = True in markers
            protocol.marked_with_errors = is_error
            protocol.logging_from_marked = logging_from_marked
            await protocol.asave()
            logger.info('Finished processing protocol id=%s', protocol.pk)
        except OperationalError as exc:
            logger.error('DB connection lost... ', exc_info=exc)
            await reconnect_db()
            protocol.classified_at = None
            asyncio.ensure_future(protocol.asave())
        except Exception as exc:  # noqa: B902  # pylint: disable=broad-exception-caught
            logger.error('Error processing protocol id=%s', protocol.pk, exc_info=exc)
            protocol.classified_at = None
            asyncio.ensure_future(protocol.asave())
    await asyncio.sleep(10)
