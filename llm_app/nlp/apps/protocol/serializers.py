from rest_framework import serializers

from nlp.apps.protocol.models import Protocol


class ProtocolSerializer(serializers.ModelSerializer):
    raw_text = serializers.CharField(write_only=True)

    class Meta:
        model = Protocol
        fields = [
            'id',
            'medcard_id',
            'user_id',
            'protocol_custom_id',
            'service_id',
            'raw_text',
            'result',
        ]


class ProtocolGraphDBSerializer(serializers.ModelSerializer):
    protocol_data = serializers.JSONField(read_only=True, source='result')

    class Meta:
        model = Protocol
        fields = [
            'medcard_id',
            'user_id',
            'protocol_custom_id',
            'service_id',
            'protocol_data',
        ]
