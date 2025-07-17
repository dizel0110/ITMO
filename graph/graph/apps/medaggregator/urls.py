from django.urls import path

from akcent_graph.apps.medaggregator.views import (
    GraphDBStructureView,
    LoadProtocolView,
    MarkDiagnosesSentView,
    MedcardNewDiagnosesView,
    NewDiagnosesByMedcardView,
    ProtocolDetailView,
)

app_name = 'medaggregator'

urlpatterns = [
    path('upload_protocol/', LoadProtocolView.as_view(), name='upload_protocol'),
    path('protocol/<str:pk>/', ProtocolDetailView.as_view(), name='get_protocol'),
    path('medcard/updated/', MedcardNewDiagnosesView.as_view(), name='updated_medcards'),
    path('medcard/<str:medcard_id>/diagnoses/', NewDiagnosesByMedcardView.as_view(), name='new_diagnoses_by_medcard'),
    path('diagnosis/update/', MarkDiagnosesSentView.as_view(), name='mark_diagnoses_sent'),
    path('structure/', GraphDBStructureView.as_view(), name='get_structure'),
]
