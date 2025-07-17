from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.views import View
from django_celery_beat.models import PeriodicTask
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from nlp.apps.protocol.models import Protocol
from nlp.apps.protocol.serializers import ProtocolSerializer
from nlp.celeryapp import app


class ProtocolView(APIView):
    serializer_class = ProtocolSerializer

    def get(self, request: Request) -> Response:
        medcard_id = request.GET.get('medcard_id')
        filters = Q(
            medcard_id=medcard_id,
            user_id=request.user.id,
            processed_at__isnull=False,
        )
        if service_id := request.GET.get('service_id', None):
            filters &= Q(service_id=service_id)
        results = Protocol.objects.filter(filters).values('id', 'service_id', 'result')
        serializer = self.serializer_class(results, many=True)
        return Response(data=serializer.data)

    def post(self, request: Request) -> Response:
        request.data['user_id'] = request.user.id
        if isinstance(request.data.get('raw_text'), list):
            try:
                request.data['raw_text'] = '\n'.join(request.data['raw_text'])
            except TypeError as err:
                return Response(data=str(err), status=status.HTTP_400_BAD_REQUEST)
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)


class ManageMainProcessView(LoginRequiredMixin, View):
    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        action = kwargs.get('action')
        if action == 'stop':
            # disable task in schedule:
            main_task = PeriodicTask.objects.filter(task='nlp.utils.LLM.tasks.process_protocols').first()
            main_task.enabled = False
            main_task.save()

            # revoke scheduled (but not yet running) tasks:
            inspect = app.control.inspect()  # type: ignore[attr-defined]
            for __, queue_task_list in inspect.scheduled().items():
                for scheduled_task in queue_task_list:
                    if scheduled_task.get('name') == 'nlp.utils.LLM.tasks.process_protocols':
                        app.control.revoke(scheduled_task.get('id'))  # type: ignore[attr-defined]

            # cancel running task:
            for __, queue_task_list in inspect.active().items():
                for active_task in queue_task_list:
                    if active_task.get('name') == 'nlp.utils.LLM.tasks.process_protocols':
                        app.control.revoke(active_task.get('id'), terminate=True)  # type: ignore[attr-defined]
            return HttpResponse('Main processing stopped. Don`t forget to resume it later!')

        if action == 'resume':
            main_task = PeriodicTask.objects.filter(task='nlp.utils.LLM.tasks.process_protocols').first()
            main_task.enabled = True
            main_task.save()
            return HttpResponse('Main processing resumed. The task will start according to the schedule')
        return HttpResponse('Unknown action...')
