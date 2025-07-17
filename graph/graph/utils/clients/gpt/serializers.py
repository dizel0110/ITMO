# pylint: disable=abstract-method
from typing import Any

from rest_framework import serializers


class YGPTAsyncTextSerializer(serializers.Serializer):
    role = serializers.CharField(required=True)
    text = serializers.CharField(required=True)


class YGPTAsyncMessageSerializer(serializers.Serializer):
    message = YGPTAsyncTextSerializer(many=False)
    status = serializers.CharField(required=True)


class YGPTAsyncUsageSerializer(serializers.Serializer):
    inputTextTokens = serializers.CharField(required=True)
    completionTokens = serializers.CharField(required=True)
    totalTokens = serializers.CharField(required=True)


class YGPTResponseSerializer(serializers.Serializer):
    alternatives = YGPTAsyncMessageSerializer(many=True)
    usage = YGPTAsyncUsageSerializer(many=False)
    modelVersion = serializers.CharField(required=True)


class YGPTAsyncResponseSerializer(YGPTResponseSerializer):
    def __init__(self, *args: tuple[Any], **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields['@type'] = serializers.CharField(required=True)


class YGPTAsyncOperationResultSerializer(serializers.Serializer):
    description = serializers.CharField(required=True)
    createdAt = serializers.CharField(required=True)
    createdBy = serializers.CharField(required=True)
    modifiedAt = serializers.CharField(required=True)
    done = serializers.BooleanField(required=True)
    metadata = serializers.BooleanField(allow_null=True, default=None)
    response = YGPTAsyncResponseSerializer(many=False)

    def __init__(self, *args: tuple[Any], **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields['id'] = serializers.CharField(required=True)


class YGPTSyncResultSerializer(serializers.Serializer):
    result = YGPTResponseSerializer(many=False)
