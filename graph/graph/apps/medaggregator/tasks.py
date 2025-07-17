import json
import logging
import uuid
from typing import Any

from celery.exceptions import Ignore, SoftTimeLimitExceeded
from constance import config
from django.conf import settings
from django.utils import timezone

from akcent_graph.apps.common.tools import get_running_task_count
from akcent_graph.apps.medaggregator.models import Diagnosis, PatientMedcard, PatientStringParam, Protocol
from akcent_graph.celeryapp import GET_UPDATED_ANAMNESES_TIMEOUT, app
from akcent_graph.utils.clients.graph_modifier.graph_crawler import NeoSpider, NeoSpiderDiseaseMatcher
from akcent_graph.utils.neo.crud_operator import Neo4jCRUD

logger = logging.getLogger(__name__)


@app.task(bind=True, ignore_results=True)
def load_new_protocols_to_graphdb(self: Any) -> None:
    # check if another instance of this task is running:
    if get_running_task_count(self.name) >= 2:
        logger.info('Another instance of this task is running. Cancelling current task...')
        raise Ignore()

    neo4jcrud = Neo4jCRUD()
    priority_users = config.PRIORITY_USERS.split()

    while Protocol.objects.filter(loaded_to_graphdb_at__isnull=True).exists():
        protocols = None
        if priority_users:
            protocols = Protocol.objects.filter(
                loaded_to_graphdb_at__isnull=True,
                patient_medcard__user_id__in=priority_users,
            )[:20]
        if not protocols:
            protocols = Protocol.objects.filter(loaded_to_graphdb_at__isnull=True)[:20]

        for protocol in protocols:
            try:
                neo4jcrud.create_nodes_and_relationships(
                    protocol.patient_medcard_id,  # type: ignore[attr-defined]
                    protocol.pk,
                    protocol.protocol_data,
                )
                protocol.loaded_to_graphdb_at = timezone.now()
                protocol.save()
            except SoftTimeLimitExceeded:
                return
            except Exception as exc:  # noqa: B902, pylint: disable=broad-exception-caught
                logger.error('Error processing protocol %s', protocol.pk, exc_info=exc)
                continue


@app.task(ignore_results=True, soft_time_limit=GET_UPDATED_ANAMNESES_TIMEOUT['seconds'])
def get_updated_anamneses_from_graphdb() -> None:
    neo4jcrud = Neo4jCRUD()
    for patient_medcard in PatientMedcard.objects.filter(
        protocols__attentions_changed=True,
        protocols__classified_at__isnull=False,
    ).distinct():
        try:
            Diagnosis.objects.filter(patient_medcard=patient_medcard).delete()
            anamnesis = neo4jcrud.get_anamnesis_by_patient_id(
                patient_medcard.pk,
            )
            logger.info(anamnesis)
            diagnoses_to_create: dict[str, Diagnosis] = {}
            string_params_to_create = []

            for object_chain_str, params in anamnesis.get('anamnesis', {}).items():
                object_chain = object_chain_str.split(settings.CHAIN_SEPARATOR)
                diagnosis_name = ' - '.join(object_chain).strip()
                diagnosis = diagnoses_to_create.setdefault(
                    diagnosis_name,
                    Diagnosis(
                        patient_medcard=patient_medcard,
                        name=diagnosis_name[:500],
                        description=diagnosis_name if len(diagnosis_name) > 500 else '',
                        # diagnosis_type=?????
                        # doctor_specialties=?????
                        # is_general=????
                    ),
                )

                default_group_id = uuid.uuid4()
                for param in params:
                    if not isinstance(group_id := param[-1], uuid.UUID):
                        group_id = default_group_id
                    if isinstance(param[1], str):
                        raw_name = param[1]
                    else:
                        raw_name = str(param[1])
                    name_feature = ' - '.join(raw_name.split(settings.CHAIN_SEPARATOR)).strip()
                    if isinstance(param[2], str):
                        value = param[2]
                    else:
                        value = str(param[2])

                    string_params_to_create.append(
                        PatientStringParam(
                            diagnosis=diagnosis,
                            group_id=group_id,
                            name=name_feature[:500] if name_feature else diagnosis_name[:500],
                            description=' '.join(
                                (
                                    part
                                    for part in (
                                        name_feature if name_feature and len(name_feature) > 500 else None,
                                        value,
                                    )
                                    if part
                                ),
                            ),
                            protocol_id=param[0],
                        ),
                    )
            Diagnosis.objects.bulk_create(diagnoses_to_create.values())
            PatientStringParam.objects.bulk_create(string_params_to_create)
            patient_medcard.protocols.update(attentions_changed=False)  # type: ignore[attr-defined]
        except SoftTimeLimitExceeded:
            return
        except Exception as exc:  # noqa: B902, pylint: disable=broad-exception-caught
            logger.error('Error fetching anamnesis for patient medcard %s', patient_medcard.pk, exc_info=exc)
            continue


@app.task(ignore_results=True, countdown=30)
def delete_test_protocol(protocol_id: int) -> None:
    Protocol.objects.filter(pk=protocol_id).delete()


@app.task(ignore_results=True)
def prepare_graphdb_structure_with_parents() -> None:
    neo4jcrud = Neo4jCRUD()
    structure = neo4jcrud.get_all_entities_by_class_names(
        exclude=[
            'NeoProtocol',
            'NeoPatient',
            'NeoDisease',
            'NeoMkb10_level_01',
            'NeoMkb10_level_02',
            'NeoMkb10_level_03',
            'NeoMkb10_level_04',
            'NeoMkb10_level_05',
            'NeoMkb10_level_06',
        ],
        with_parents=False,
    )
    if not structure:
        logger.warning('Structure fetch failed or GraphDB is empty')
        return
    with open(settings.GRAPHDB_STRUCTURE_JSON, 'w', encoding='utf8') as file:
        json.dump(structure, file, ensure_ascii=False)


@app.task(ignore_results=True)
def neospider_check_and_change() -> None:
    try:
        neospider = NeoSpider()
        neospider.check_and_change()
    except Exception as exc:  # noqa: B902, pylint: disable=broad-exception-caught
        logger.error('Error occured during neospider_check_and_change task', exc_info=exc)


@app.task(ignore_results=True)
def neospider_delete_brief_doubles() -> None:
    try:
        neospider = NeoSpider()
        neospider.delete_brief_doubles()
    except Exception as exc:  # noqa: B902, pylint: disable=broad-exception-caught
        logger.error('Error occured during neospider_delete_brief_doubles task', exc_info=exc)


@app.task(ignore_results=True)
def neospider_neodisease_nodes_checker() -> None:
    try:
        neospider_disease_matcher = NeoSpiderDiseaseMatcher()
        neospider_disease_matcher.neodisease_nodes_checker()
    except Exception as exc:  # noqa: B902, pylint: disable=broad-exception-caught
        logger.error('Error occured during neospider_neodisease_nodes_checker task', exc_info=exc)
