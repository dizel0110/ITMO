import json
import os.path
from typing import Any

from django.conf import settings
from django.db.models import Q, QuerySet
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from akcent_graph.apps.medaggregator.helpers import NEO_CLASS_NAMES
from akcent_graph.apps.medaggregator.models import Diagnosis, PatientMedcard, Protocol
from akcent_graph.apps.medaggregator.permissions import IsNeuroUser
from akcent_graph.apps.medaggregator.serializers import DiagnosisSerializer, ProtocolSerializer
from akcent_graph.apps.medaggregator.tasks import delete_test_protocol


class LoadProtocolView(APIView):
    """
    Endpoint exclusively for Neuro
    """

    permission_classes = (IsAuthenticated, IsNeuroUser)

    def post(self, request: Request) -> Response:
        serializer = ProtocolSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        critical_errors = []
        warnings = []
        refined_data = []
        for entry in request.data.get('protocol_data', []):
            if 'class' not in entry:
                critical_errors.append({'entry': entry, 'error': '`class` key is missing'})
                continue
            if entry['class'] in {'NeoPatient', 'NeoProtocol'}:
                warnings.append({'entry': entry, 'error': 'Redundant classes: NeoPatient/NeoProtocol'})
                continue
            if entry['class'] not in NEO_CLASS_NAMES:
                critical_errors.append({'entry': entry, 'error': f'Unknown class name: {entry["class"]}'})
                continue
            refined_data.append(entry)
        if critical_errors or not refined_data:
            return Response(critical_errors + warnings, status=status.HTTP_400_BAD_REQUEST)

        request.data['protocol_data'] = refined_data
        serializer = ProtocolSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        protocol = serializer.save()
        if refined_data[0].get('name') == '269a0e7a-82b1-4cd0-9013-8098f9cbd4c0':
            delete_test_protocol.apply_async(args=(protocol.pk,), queue='high')
        return Response(warnings, status=status.HTTP_201_CREATED)


class ProtocolDetailView(APIView):
    """
    Endpoint exclusively for Neuro
    """

    permission_classes = (IsAuthenticated, IsNeuroUser)

    def get(self, request: Request, **kwargs: Any) -> Response:
        protocol = Protocol.objects.filter(protocol_custom_id=kwargs['pk']).first()
        if not protocol:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = ProtocolSerializer(protocol)
        return Response(data=serializer.data)


class MedcardNewDiagnosesView(APIView):
    def get(self, request: Request, **kwargs: Any) -> Response:
        updated_medcards = list(
            PatientMedcard.objects.filter(
                diagnoses__is_sent_to_lk=False,
                user_id=request.user.id,
            )
            .distinct()
            .values_list('medcard_id', flat=True),
        )
        return Response(data=updated_medcards)


class NewDiagnosesByMedcardView(ListAPIView):
    serializer_class = DiagnosisSerializer

    def get_queryset(self) -> QuerySet[Diagnosis]:
        filters = Q(
            patient_medcard__medcard_id=self.kwargs['medcard_id'],
            patient_medcard__user_id=self.request.user.id,
        )
        if 'force_refetch' not in self.request.query_params:
            filters &= Q(is_sent_to_lk=False)
        return (
            Diagnosis.objects.filter(filters)
            .select_related('patient_medcard')
            .prefetch_related('protocols', 'string_params__protocol', 'digital_params__protocol')
        )


class MarkDiagnosesSentView(APIView):
    def post(self, request: Request, **kwargs: Any) -> Response:
        Diagnosis.objects.filter(
            pk__in=request.data,
            patient_medcard__user_id=request.user.id,
        ).update(is_sent_to_lk=True)
        return Response(status=status.HTTP_200_OK)


class GraphDBStructureView(APIView):
    """
    Endpoint exclusively for Neuro
    """

    permission_classes = (IsAuthenticated, IsNeuroUser)

    def get(self, request: Request, **kwargs: Any) -> Response:
        if not os.path.exists(settings.GRAPHDB_STRUCTURE_JSON):
            return Response('File not found', status=status.HTTP_404_NOT_FOUND)
        with open(settings.GRAPHDB_STRUCTURE_JSON, 'r', encoding='utf8') as file:
            structure = json.load(file)

        return Response(data=structure)
