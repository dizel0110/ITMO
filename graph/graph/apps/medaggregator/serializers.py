from typing import Any, Optional

from django.db.utils import IntegrityError
from rest_framework import serializers

from akcent_graph.apps.medaggregator.models import (
    Diagnosis,
    PatientDigitalParam,
    PatientMedcard,
    PatientStringParam,
    Protocol,
)


class ProtocolSerializer(serializers.ModelSerializer):
    medcard_id = serializers.CharField(source='patient_medcard.medcard_id')
    user_id = serializers.CharField(source='patient_medcard.user_id')

    class Meta:
        model = Protocol
        fields = [
            'medcard_id',
            'user_id',
            'protocol_custom_id',
            'service_id',
            'protocol_data',
            'is_medtest',
        ]

    def save(self, **kwargs: Any) -> Protocol:
        patient_medcard, __ = PatientMedcard.objects.get_or_create(**self.validated_data['patient_medcard'])
        self.validated_data['patient_medcard'] = patient_medcard
        try:
            super().save(**kwargs)
        except IntegrityError:
            self.instance = Protocol.objects.get(
                patient_medcard=patient_medcard,
                protocol_custom_id=self.validated_data['protocol_custom_id'],
            )
            super().save(**kwargs)
        return self.instance


class BasePatientParamSerializer(serializers.ModelSerializer):
    protocol = serializers.SerializerMethodField('get_protocol')
    parent_medtest = serializers.SerializerMethodField('get_medtest')

    def get_protocol(self, obj: Any) -> Optional[str]:
        if not obj.protocol.is_medtest:
            return obj.protocol.protocol_custom_id
        return None

    def get_medtest(self, obj: Any) -> Optional[str]:
        if obj.protocol.is_medtest:
            return obj.protocol.protocol_custom_id
        return None


class PatientStringParamSerializer(BasePatientParamSerializer):
    class Meta:
        model = PatientStringParam
        fields = ['group_id', 'name', 'description', 'protocol', 'parent_medtest']


class PatientDigitalParamSerializer(BasePatientParamSerializer):
    class Meta:
        model = PatientDigitalParam
        fields = [
            'group_id',
            'name',
            'value',
            'protocol',
            'parent_medtest',
        ]


class DiagnosisSerializer(serializers.ModelSerializer):
    medcard_id = serializers.CharField(source='patient_medcard.medcard_id')
    user_id = serializers.CharField(source='patient_medcard.user_id')
    protocols = serializers.SerializerMethodField('get_custom_protocol_ids')
    parent_medtests = serializers.SerializerMethodField('get_parent_medtest_ids')
    string_params = PatientStringParamSerializer(many=True)
    digital_params = PatientDigitalParamSerializer(many=True)
    doctor_specialties = serializers.SerializerMethodField('get_doctor_specialties')
    diagnosis_id = serializers.IntegerField(source='id')

    class Meta:
        model = Diagnosis
        fields = [
            'diagnosis_id',
            'medcard_id',
            'user_id',
            'name',
            'description',
            'date_created',
            'diagnosis_type',
            'protocols',
            'parent_medtests',
            'string_params',
            'digital_params',
            'doctor_specialties',
            'is_general',
        ]

    def get_custom_protocol_ids(self, obj: Diagnosis) -> list[str]:
        return list(obj.protocols.filter(is_medtest=False).values_list('protocol_custom_id', flat=True))

    def get_parent_medtest_ids(self, obj: Diagnosis) -> list[str]:
        return list(obj.protocols.filter(is_medtest=True).values_list('protocol_custom_id', flat=True))

    def get_doctor_specialties(self, obj: Diagnosis) -> list[str]:
        return list(obj.doctor_specialties.values_list('name', flat=True))
