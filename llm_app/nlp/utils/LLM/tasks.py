import asyncio
import logging
import os
import traceback
from datetime import timedelta
from functools import cache as ft_cache
from random import randint
from typing import Any, Optional

import aiohttp
import pandas as pd
from asgiref.sync import sync_to_async
from celery.exceptions import Ignore
from constance import config
from django.conf import settings
from django.db import connections
from django.db.models import Q
from django.db.utils import OperationalError
from django.utils import timezone

from nlp.apps.protocol.models import ParsingError, Protocol
from nlp.apps.secret_settings.models import DBEntities, DBStructure, GlobalProcessingSettings
from nlp.apps.secret_settings.tasks import refresh_graphdb_structure
from nlp.celeryapp import app
from nlp.utils.LLM.Embedder import EmbeddingModel
from nlp.utils.LLM.feature_extactor.feature_extractor import AnswerParsingError, AsyncFeatureExtractor
from nlp.utils.LLM.feature_extactor.feature_unifier import AsyncFeatureUnifier
from nlp.utils.LLM.llm_answer_parsing import merge_and_transform_data
from nlp.utils.LLM.llm_rephrase import AsyncRephrase

logger = logging.getLogger(__name__)


@ft_cache
def get_extractor() -> AsyncFeatureExtractor:
    return AsyncFeatureExtractor()


@ft_cache
def get_unifier() -> AsyncFeatureUnifier:
    return AsyncFeatureUnifier()


@ft_cache
def get_rephrase() -> AsyncRephrase:
    return AsyncRephrase()


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


@sync_to_async
def get_priority_users() -> list[str]:
    return config.PRIORITY_USERS.split()


async def take_protocol() -> None:
    await asyncio.sleep(randint(50, 1000) / 1000)
    priority_users = await get_priority_users()
    protocol = None
    if priority_users:
        protocol = (
            await Protocol.objects.filter(
                processed_at__isnull=True,
                user_id__in=priority_users,
            )
            .order_by('id')
            .afirst()
        )
    if not protocol:
        protocol = await Protocol.objects.filter(processed_at__isnull=True).order_by('id').afirst()

    if protocol:
        asyncio.ensure_future(process_protocol_async(protocol))
        return
    logger.info('There are no more protocols...')


async def loop_controller(batch: int) -> None:
    """
    1) Checks the number of running `process_protocol_async` tasks;
    2) If all tasks done - stops the event loop and finalizes `process_protocols_async` celery task;
    3) If number of running tasks less than batch value and a new bunch of protocols arrives -
    increases number os tasks up to bunch value;
    """
    while True:
        await asyncio.sleep(60)
        if (running_tasks_count := sum(1 for task in asyncio.all_tasks() if not task.done())) <= 1:
            logger.info('All tasks done. Stopping event loop...')
            asyncio.get_event_loop().stop()
            break
        logger.info('Running tasks count: %s', running_tasks_count)
        if running_tasks_count < batch + 1:
            asyncio.ensure_future(
                run_process_protocols(batch + 1 - running_tasks_count),
            )


async def process_protocol_async(  # noqa: C901
    protocol: Protocol,
    take_next: bool = True,
) -> None:
    """
    Process protocol through pipeline with mandatory final parsing and merging

    Pipeline:
    1. Optional rephrasing
    2. Feature extraction by windows - returns list of JSON strings
    3. Optional unification - returns list of JSON strings for each input JSON
    4. Mandatory: Parse all JSONs
    5. Mandatory: Merge all objects with ID fixing, handling empty results
    6. Save result
    """
    active_settings = await GlobalProcessingSettings.objects.filter(is_active=True).afirst()
    processed_text = protocol.raw_text

    logger.info('Processing protocol id=%s...', protocol.pk)

    try:
        protocol.processed_at = timezone.now()
        asyncio.ensure_future(protocol.asave())
        asyncio.ensure_future(protocol.structure_errors.all().adelete())  # type: ignore[attr-defined]

        # Optional rephrasing
        if active_settings and active_settings.rephrase:
            rephrase = get_rephrase()
            processed_text = await rephrase.pipe(processed_text)
            if not processed_text:
                logger.error('Empty text after rephrasing')
                if take_next:
                    asyncio.ensure_future(take_protocol())
                return

        # Get list of JSON strings from extractor
        extractor = get_extractor()
        use_sliding = active_settings.shifted_window if active_settings else True
        json_results = await extractor.pipe(processed_text, use_sliding_window=use_sliding)
        extraction_res = json_results

        if not json_results:
            logger.error('No extracted results')
            if take_next:
                asyncio.ensure_future(take_protocol())
            return

        # Optional unification
        if active_settings and active_settings.unification:
            unifier = get_unifier()
            # For each JSON from extractor, get list of JSONs from unifier
            unified_lists = []
            for json_str in json_results:
                unified_lists.append(await unifier.pipe(json_str))
            # Flatten list of lists into single list, filtering out None results
            json_results = [
                json_str for unified_list in unified_lists if unified_list is not None for json_str in unified_list
            ]
            final_result = merge_and_transform_data(extraction_res, json_results)  # type: ignore[arg-type]
        else:
            final_result = merge_and_transform_data(extraction_res)  # type: ignore[arg-type]

        logger.error('Final Result: %s', final_result)

        protocol.result = final_result
        protocol.is_sent_to_graphdb = False
        protocol.is_saved_to_graphdb = False
        await protocol.asave()
        logger.info('Finished processing protocol id=%s', protocol.pk)
    except aiohttp.ClientError as exc:
        logger.error('Error contacting the LLM service while processing protocol id=%s', protocol.pk, exc_info=exc)
        pause = randint(700, 2000)
        logger.warning('Coroutine paused for %s ms', pause)
        await asyncio.sleep(pause / 1000)
        protocol.processed_at = None
        asyncio.ensure_future(protocol.asave())
    except AnswerParsingError as exc:
        logger.error('Error processing protocol id=%s: ', protocol.pk, exc_info=exc)
        protocol.parsing_error_count += 1
        asyncio.ensure_future(protocol.asave())
        asyncio.ensure_future(
            ParsingError.objects.acreate(
                protocol=protocol,
                error_type=type(exc).__name__,
                error_message=str(exc),
                traceback=traceback.format_exc(),
                llm_response=exc.llm_response,
            ),
        )
    except OperationalError as exc:
        logger.error('DB connection lost... ', exc_info=exc)
        await reconnect_db()
        asyncio.ensure_future(
            ParsingError.objects.acreate(
                protocol=protocol,
                error_type=type(exc).__name__,
                error_message=str(exc),
                traceback=traceback.format_exc(),
            ),
        )
    except Exception as exc:  # noqa: B902 pylint: disable=broad-exception-caught
        logger.error('Error processing protocol id=%s: ', protocol.pk, exc_info=exc)
    if take_next:
        await take_protocol()


async def run_process_protocols(batch: int) -> None:
    try:
        protocols = Protocol.objects.filter(processed_at__isnull=True).order_by('id')[:batch]
        async for protocol in protocols:
            asyncio.ensure_future(process_protocol_async(protocol))

    except OperationalError as exc:
        logger.error('DB connection lost.. ', exc_info=exc)
        await reconnect_db()
        asyncio.ensure_future(run_process_protocols(batch))


# Do not rename this task!
@app.task(bind=True, ignore_results=True, soft_time_limit=999900, time_limit=999999)
def process_protocols(self: Any) -> None:
    # check if another instance of this task is running:
    inspect = app.control.inspect()  # type: ignore[attr-defined]
    task_count = 0
    for __, queue_task_list in inspect.active().items():
        for active_task in queue_task_list:
            if active_task.get('name') == self.name:
                task_count += 1
                if task_count >= 2:
                    logger.info('Another instance of this task is running. Cancelling current task...')
                    raise Ignore()

    if not Protocol.objects.filter(processed_at__isnull=True).exists():
        logger.info('There are no new protocols.')
        return

    if not DBStructure.objects.filter(name='entities').exists():
        logger.warning('GraphDB structure not found. Refresh procedure scheduled. Aborting task...')
        refresh_graphdb_structure.apply_async(queue='high')
        return

    get_extractor()  # must be first called from sync context!
    get_unifier()  # must be first called from sync context!
    get_rephrase()  # must be first called from sync context!
    loop = asyncio.new_event_loop()
    loop.create_task(run_process_protocols(config.BATCH_SIZE))
    loop.create_task(loop_controller(config.BATCH_SIZE))
    loop.run_forever()


@app.task(ignore_results=True)
def return_failed_protocols_to_processing() -> None:
    if Protocol.objects.filter(processed_at__isnull=True).exists():
        logger.info('Unprocessed protocols found')
        return
    filters = Q(processed_at__lt=timezone.now() - timedelta(minutes=60)) & Q(result__isnull=True)
    if config.MAX_PARSING_ERRORS:
        filters &= Q(parsing_error_count__lt=config.MAX_PARSING_ERRORS)
    if config.MAX_API_ERRORS:
        filters &= Q(parsing_error_count__lt=config.MAX_API_ERRORS)
    Protocol.objects.filter(filters).update(processed_at=None)


@app.task(ignore_results=True, soft_time_limit=999900, time_limit=999999)
def process_protocol_list(protocol_ids: list[int]) -> None:
    if not protocol_ids:
        return

    get_extractor()  # must be first called from sync context!
    get_unifier()  # must be first called from sync context!
    get_rephrase()  # must be first called from sync context!
    batch = config.BATCH_SIZE
    asyncio.run(process_protocol_list_async(protocol_ids, batch))


async def send_protocol_to_processing_by_id(semaphore: asyncio.Semaphore, protocol_id: int) -> None:
    async with semaphore:
        protocol = await Protocol.objects.filter(pk=protocol_id).afirst()
        if protocol:
            await process_protocol_async(protocol, take_next=False)


async def process_protocol_list_async(protocol_ids: list[int], batch: int) -> None:
    semaphore = asyncio.Semaphore(batch)
    await asyncio.gather(*[send_protocol_to_processing_by_id(semaphore, protocol_id) for protocol_id in protocol_ids])


@app.task(ignore_results=True)
def update_entities_pkl() -> None:
    """
    Get all entities that are not loaded yet.
    Create a pickle if it does not exist yet.
    Load a pickle. Add new embeddings to the pickle.

    """
    if not DBEntities.objects.filter(uploaded_to_pkl=False).exists():
        return
    if not os.path.exists(settings.ANNOY_DATA_PATH):
        name_folder, __ = os.path.split(settings.ANNOY_DATA_PATH)
        os.makedirs(name_folder, exist_ok=True)
        entities = pd.DataFrame(
            columns=[
                'Class',
                'embedding_query_v1',
                'name_class',
                'parents',
                'index',
            ],
        )
        entities.to_pickle(settings.ANNOY_DATA_PATH)

    embedder = EmbeddingModel()
    batch = config.EMBEDDINGS_BATCH_SIZE
    asyncio.run(update_entities_plk_async(embedder, batch))


async def update_entities_plk_async(embedder: EmbeddingModel, batch: int) -> None:
    semaphore = asyncio.Semaphore(batch)
    coro_list = []
    async for entity in DBEntities.objects.filter(uploaded_to_pkl=False):
        coro_list.append(process_entity_pkl(entity, semaphore, embedder))
    embeddings = await asyncio.gather(*coro_list)
    with open(settings.ANNOY_DATA_PATH, 'rb') as file:
        entities = pd.read_pickle(file)
    for name, embedding, entity_class, parents, index in embeddings:
        if not name:
            continue
        entities.loc[entities.shape[0]] = [
            name,
            embedding,
            entity_class,
            parents,
            index,
        ]
    entities.to_pickle(settings.ANNOY_DATA_PATH)


async def process_entity_pkl(
    entity: DBEntities,
    semaphore: asyncio.Semaphore,
    embedder: EmbeddingModel,
) -> tuple[Optional[str], Optional[Any], Optional[str], Optional[list[int]], Optional[int]]:
    async with semaphore:
        try:
            embedding = await embedder.embed_document(entity.name)
        except Exception as exc:  # noqa B902
            logger.error('Error processing entity %s, id=%s', entity.name, entity.pk, exc_info=exc)
            return None, None, None, None, None
        if not embedding:
            return None, None, None, None, None

        entity.uploaded_to_pkl = True
        asyncio.ensure_future(entity.asave())
        return entity.name, embedding, entity.entity_class, entity.parents, entity.pk
