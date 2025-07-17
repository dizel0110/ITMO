from typing import Any

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from akcent_graph.apps.common.models import User
from akcent_graph.apps.medaggregator.models import (
    Diagnosis,
    PatientDigitalParam,
    PatientMedcard,
    PatientStringParam,
    Protocol,
    Speciality,
)


@pytest.fixture
@pytest.mark.django_db
def prepare_test_data(request):
    request.cls.user = User.objects.create_user(username='testuser', password='12345')
    token = str(RefreshToken.for_user(request.cls.user).access_token)
    request.cls.headers = {'Authorization': f'Bearer {token}'}

    patient_medcard = PatientMedcard.objects.create(
        medcard_id='12345',
        user_id=request.cls.user.pk,
    )
    PatientMedcard.objects.create(
        medcard_id='67890',
        user_id=request.cls.user.pk,
    )
    protocol1 = Protocol.objects.create(
        patient_medcard=patient_medcard,
        protocol_custom_id='protocol1',
        service_id=111,
        protocol_data={},
    )
    protocol2 = Protocol.objects.create(
        patient_medcard=patient_medcard,
        protocol_custom_id='protocol2',
        service_id=222,
        protocol_data={},
        is_medtest=True,
    )
    request.cls.diagnosis = Diagnosis.objects.create(
        patient_medcard=patient_medcard,
        name='Пневмония',
        description='Атипичная пневмония',
        date_created='2024-12-31',
        is_general=False,
        diagnosis_type=0,
    )
    request.cls.diagnosis.protocols.set([protocol1, protocol2])
    request.cls.diagnosis.doctor_specialties.set(Speciality.objects.filter(pk__in=(2, 3)))
    PatientStringParam.objects.create(
        diagnosis=request.cls.diagnosis,
        group_id='g123',
        name='Антитела',
        description='положительно',
        protocol=protocol1,
    )
    PatientDigitalParam.objects.create(
        diagnosis=request.cls.diagnosis,
        group_id='g456',
        name='Гемоглобин',
        value=110,
        protocol=protocol2,
    )


@pytest.mark.usefixtures('prepare_test_data')
@pytest.mark.django_db
class TestLkAPI:
    def test_medcard_new_diagnoses_view(self, client: APIClient, mocker: Any):
        mock_cache = mocker.patch('django.core.cache.cache.get')
        mock_cache.return_value = True
        response = client.get(
            reverse('medaggregator:updated_medcards'),
            headers=self.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == ['12345']

    def test_new_diagnoses_by_medcard_view(self, client: APIClient, mocker: Any):
        mock_cache = mocker.patch('django.core.cache.cache.get')
        mock_cache.return_value = True
        response = client.get(
            reverse('medaggregator:new_diagnoses_by_medcard', args=('12345',)),
            headers=self.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [
                {
                    'diagnosis_id': self.diagnosis.pk,
                    'medcard_id': '12345',
                    'user_id': str(self.user.pk),
                    'name': 'Пневмония',
                    'description': 'Атипичная пневмония',
                    'date_created': timezone.localdate().isoformat(),
                    'diagnosis_type': 0,
                    'protocols': ['protocol1'],
                    'parent_medtests': ['protocol2'],
                    'string_params': [
                        {
                            'group_id': 'g123',
                            'name': 'Антитела',
                            'description': 'положительно',
                            'protocol': 'protocol1',
                            'parent_medtest': None,
                        },
                    ],
                    'digital_params': [
                        {
                            'group_id': 'g456',
                            'name': 'Гемоглобин',
                            'value': '110.00',
                            'protocol': None,
                            'parent_medtest': 'protocol2',
                        },
                    ],
                    'doctor_specialties': [
                        'главный врач',
                        'врач-акушер-гинеколог',
                    ],
                    'is_general': False,
                },
            ],
        }

    def test_mark_diagnoses_sent_view(self, client: APIClient, mocker: Any):
        mock_cache = mocker.patch('django.core.cache.cache.get')
        mock_cache.return_value = True
        response = client.post(
            reverse('medaggregator:mark_diagnoses_sent'),
            data=[self.diagnosis.pk],
            format='json',
            headers=self.headers,
        )
        assert response.status_code == status.HTTP_200_OK
