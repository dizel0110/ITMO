# pylint: disable=duplicate-code
"""
Module for testing of assembly of prompts.
==========================================

Classes:
----------
TestPrompt:
    \n\ttest_get_prompt_of_description_extract
    \n\ttest_get_prompt_of_entities_classifier

Dependencies:
-------------
django

"""


from django.test.testcases import TestCase

from akcent_graph.utils.clients.gpt.prompts import get_prompt_of_description_extract, get_prompt_of_entities_classifier


class TestPrompt(TestCase):
    """
    Tests for akcent_graph.utils.clients.gpt.prompts.py
    ================================================

    Methods:
    --------
    \n\ttest_get_prompt_of_description_extract
    \n\ttest_get_prompt_of_entities_classifier

    """

    def setUp(self) -> None:
        self.anamnesis = '{"щитовидная железа - объем": \
            [[235001, "щитовидная железа - объем", "12.1 см3", "2024-12-05", 2], \
            [235100, "щитовидная железа - правая доля - размеры", "1.7 х 1.6 х 4.7 см", "2024-12-05", 2]], \
            "щитовидная железа - левая доля - размеры": \
            [[235001, "щитовидная железа - левая доля - размеры", "1.7 х 1.6 х 5.0 см", "2024-12-05", 1], \
            [235002, "щитовидная железа - левая доля - размеры", "1.8 х 1.6 х 5.2 см", "2024-12-06", 2]]}'
        self.disease = 'Болезнь щитовидной железы неуточненная'
        self.extract_sample = (
            '6. Полный диагноз (основное заболевание, сопутствующее осложнение).',
            '7. Краткий анамнез, диагностические исследования, течение болезни, проведенное лечение, '
            'состояние при направлении, при выписке.',
            '8. Лечебные и трудовые рекомендации:',
        )
        self.daughter_entity = 'митральный клапан'
        self.parent_entity = 'сердце'

    def test_get_prompt_of_description_extract(self) -> None:
        anamnesis = self.anamnesis
        disease = self.disease
        extract_sample = self.extract_sample

        answer_system_prompt = f'Ты высоквалифицированный врач. Напиши три пункта в медицинской выписке. В качестве названия пунктов используй элементы кортежа {extract_sample}.\n Не дроби пункты на подпункты. Соблюдай нумерацию, как в образце.'
        answer_prompt = f'У Тебя есть болезнь {disease} и соответсвующий болезни анамнез {anamnesis} для генерации медицинской выписки пациента только согласно образцу {extract_sample}!\n На основании этих данных  создай элементы медицинской выписки следующего формата, названия обязательно такие же:\n В пункте 6. образца напиши только {disease}\n в пукнтках 7. и 8. образца воспользуйся данными из анамнеза\n В пункте 8., если есть на то основание из данных анамнеза укажи консультацию рекомендуемого специалиста\n Всё что связано с числовыми результатами не описывай только словами.\n Включи динамику числовых показателей из анамнеза.\n Если встретишь код МКБ, преобразуй в название болезни.\n Нет информации, оставляй незаполненным пункт.'

        prompt, system_prompt = get_prompt_of_description_extract(
            anamnesis=anamnesis,
            disease=disease,
            extract_sample=extract_sample,
        )

        self.assertEqual(
            answer_prompt,
            prompt,
        )

        self.assertEqual(
            answer_system_prompt,
            system_prompt,
        )

    def test_get_prompt_of_entities_classifier(self) -> None:
        daughter_entity = self.daughter_entity
        parent_entity = self.parent_entity

        answer_prompt = f'Проведи бинарную классификацию. В результате ты должен выдать 0 типа int, если родительская сущность с именем {parent_entity} не связана с дочерней сущностью {daughter_entity}. В обратном случае выдай 1 типа int, но только, если дочерняя сущность является и частью родительской сущности и её логическим продолжением. В качестве примера в палате могут быть пациента, но в пациентах не может быть палата. Также митральный клапан часть сердца, но сердце не часть митрального клапана.'
        answer_system_prompt = f'Ты высоквалифицированный врач. Твоя задача провести бинарную классификацию, может ли родительская сущность с именем {parent_entity} быть связана с потенциальной дочерней сущностью с именем {daughter_entity} с медицинcкой точки зрения. Дочерняя сущность не должна содержать в себе родительскую сущность. Это всегда 0. Сомневаешься, что ставить, ставь 0. Если для проведения бинарной классификации необходимо больше информации, ставь 0!!!!!'

        prompt, system_prompt = get_prompt_of_entities_classifier(
            daughter_entity=daughter_entity,
            parent_entity=parent_entity,
        )

        self.assertEqual(
            answer_prompt,
            prompt,
        )

        self.assertEqual(
            answer_system_prompt,
            system_prompt,
        )
