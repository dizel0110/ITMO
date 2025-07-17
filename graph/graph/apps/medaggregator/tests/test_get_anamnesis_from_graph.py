# from typing import Any

import pytest

from akcent_graph.apps.medaggregator.models import PatientMedcard, Protocol  # Diagnosis, PatientStringParam,

# from akcent_graph.apps.medaggregator.tasks import get_updated_anamneses_from_graphdb


@pytest.fixture
@pytest.mark.django_db
def test_anamnesis(request):
    request.cls.patient_medcard = PatientMedcard.objects.create()

    protocol_ids = [
        Protocol.objects.create(
            patient_medcard=request.cls.patient_medcard,
            protocol_custom_id='',
            protocol_data={},
            classified_at='2024-12-18T00:00:00+00:00',
            attentions_changed=True,
        ).pk
        for __ in range(4)
    ]

    request.cls.anamnesis = {
        'diseases': {
            'атеросклероз сосудов': [
                protocol_ids[0],
                protocol_ids[1],
                protocol_ids[2],
            ],
        },
        'anamnesis': {
            'щитовидная железа - объем': [
                [protocol_ids[0], 'щитовидная железа - объем', '12.1 см3', '2024-12-16 10:22:27.603127', 2],
                [protocol_ids[1], 'щитовидная железа - объем', '12.8 см3', '2024-12-16 10:22:29.767128', 2],
                [protocol_ids[2], 'щитовидная железа - объем', '12.9 см3', '2024-12-16 10:22:31.857839', 2],
                [protocol_ids[3], 'щитовидная железа - объем', '12.93 см3', '2024-12-16 10:22:33.921382', 2],
            ],
            'щитовидная железа - правая доля - размеры': [
                [
                    protocol_ids[0],
                    'щитовидная железа - правая доля - размеры',
                    '1.6 х 1.7 х 5.2 см',
                    '2024-12-16 10:22:27.848425',
                    1,
                ],
                [
                    protocol_ids[1],
                    'щитовидная железа - правая доля - размеры',
                    '1.7 х 1.8 х 5.2 см',
                    '2024-12-16 10:22:29.999650',
                    1,
                ],
                [
                    protocol_ids[2],
                    'щитовидная железа - правая доля - размеры',
                    '1.8 х 1.9 х 5.2 см',
                    '2024-12-16 10:22:32.074890',
                    1,
                ],
                [
                    protocol_ids[3],
                    'щитовидная железа - правая доля - размеры',
                    '1.7 х 1.6 х 4.7 см',
                    '2024-12-16 10:22:33.761599',
                    2,
                ],
            ],
            'щитовидная железа - левая доля - размеры': [
                [
                    protocol_ids[0],
                    'щитовидная железа - левая доля - размеры',
                    '1.7 х 1.6 х 5.0 см',
                    '2024-12-16 10:22:27.380640',
                    1,
                ],
                [
                    protocol_ids[1],
                    'щитовидная железа - левая доля - размеры',
                    '1.8 х 1.6 х 5.2 см',
                    '2024-12-16 10:22:29.586557',
                    2,
                ],
                [
                    protocol_ids[2],
                    'щитовидная железа - левая доля - размеры',
                    '2.0 х 1.8 х 5.0 см',
                    '2024-12-16 10:22:31.700089',
                    1,
                ],
                [
                    protocol_ids[3],
                    'щитовидная железа - левая доля - размеры',
                    '1.7 х 1.6 х 5.0 см',
                    '2024-12-16 10:22:33.607549',
                    2,
                ],
            ],
        },
    }


# @pytest.mark.usefixtures('test_anamnesis')
# @pytest.mark.django_db
# class TestGetAnamnesisAPI:
#     def test_get_anamnesis(self, mocker: Any, settings: Any):
#         settings.CHAIN_SEPARATOR = ' - '
#         mock_neo4jcrud = mocker.patch('akcent_graph.utils.neo.crud_operator.Neo4jCRUD.get_anamnesis_by_patient_id')
#         mock_neo4jcrud.return_value = self.anamnesis

#         get_updated_anamneses_from_graphdb()

#         assert Diagnosis.objects.count() == 2
#         assert PatientStringParam.objects.count() == 15
#         assert list(Diagnosis.objects.values_list('name', flat=True)) == [
#             'Перенесенные заболевания',
#             'щитовидная железа',
#         ]
#         assert (
#             PatientStringParam.objects.filter(diagnosis__name='Перенесенные заболевания').first().name
#             == 'атеросклероз сосудов'
#         )
#         assert sorted(
#             list(
#                 PatientStringParam.objects.filter(diagnosis__name='щитовидная железа')
#                 .distinct('name')
#                 .values_list('name', flat=True),
#             ),
#         ) == [
#             'левая доля - размеры',
#             'объем',
#             'правая доля - размеры',
#         ]
