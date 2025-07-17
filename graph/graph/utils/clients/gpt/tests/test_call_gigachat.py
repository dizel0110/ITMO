"""GigaChat tests for authentication and embedding.
================================================

Classes:
----------
CatboostTests :
    \n\tsetUp
    \n\ttest_auth
    \n\ttest_broken_auth
    \n\ttest_big_emb
    \n\ttest_emb

"""

from typing import Optional

from django.test.testcases import TestCase

from akcent_graph.utils.clients.gpt.call_gigachat import GigaChat


class GigaChatTests(TestCase):
    """Test GigaChat.
    ===================================================

    Methods:
    --------
    \n\tsetUp
    \n\ttest_auth
    \n\ttest_broken_auth
    \n\ttest_big_emb
    \n\ttest_emb

    """

    def setUp(self) -> None:
        self.gigachat = GigaChat()

    def test_auth(self) -> None:
        gigachat = GigaChat()
        token = gigachat.gen_token()
        self.assertTrue(isinstance(token, Optional[str]), 'token is not a string or None')

    def test_broken_auth(self) -> None:
        gigachat = GigaChat()
        true_api = gigachat.api_key

        gigachat.api_key = 'abcdef'
        token = gigachat.gen_token()
        gigachat.api_key = true_api

        self.assertTrue(token is None, 'token is not None, when it should be (broken url)')

    def test_big_emb(self) -> None:
        gigachat = GigaChat()

        conclusion = """
                Описание:
                Рост: 154 см. Вес: 80 кг. ППТ: 1.78м2.
                Аорта на уровне синусов Вальсальвы 2.3 см.
                Левое предсердие 3.1 см в парастернальной позиции, 3.8 х 4.8 см в четырехкамерной позиции.
                Объем ле- вого предсердия 43 мл. Индекс объема ЛП 24.16 мл/м2. Правое предсердие 3.8 х 4.8 см,
                в четырехкамерной позиции .
                Правый желудочек (В-режим) 2.9 см, в парастернальной позиции. Толщина миокарда ПЖ в диастолу 0.25 см.
                Время ускорения в ЛА 121 мсек. Систолическое давление в ПЖ 29 мм рт.ст. по трикуспидальной регур-
                гитации. Признаки легочной гипертензии не выявлены.
                Левый желудочек: КДР: 4.2 см. КСР: 2.6 см. КДО 78 мл., КСО 25 мл.
                Толщина миокарда ЛЖ в диастолу 0.9 см. ММЛЖ: 118.67 гр. ИММЛЖ: 66.67 гр/м2.
                Систолическая функция ЛЖ (метод Тейхгольца): УО 54 мл. ФВ 69 %. Метод Симпсона УО 53 мл. ФВ 65 %.
                Тип выброса 1.38 м/с, гиперкинетический.
                TDI: систолическая скорость 11.0 cм/с латеральной части левого фиброзного кольца.
                Диастолическая функция ЛЖ: тип наполнения 1.14/ 1.09 м/с, промежуточный. ВИВР неинформативно. TDI:
                диастолические скорости движения: е'/a' 10.0/12.0 cм/с латеральной части левого фиброзного коль- ца,
                е'/a' септальной части левого фиброзного кольца 9.0/12.0 cм/с.
                Средняя диастолическая скорость движения левого фиброзного кольца в раннюю диастолу e' 9.50 см/с.
                Индекс наполнения левого желудочка E/e' 12.00.
                Зоны акинезии не выявлены.
                Клапанный аппарат:
                Аортальный клапан: створки не уплотнены подвижны, расхождение 1.5 см. Поток через клапан ламинар- ный.
                Митральный клапан: створки не уплотнены, подвижны, движение дискордантное, расхождение 2.3 см.
                Поток через клапан ламинарный.Физиологическая регургитация.
                Трикуспидальный клапан: створки не изменены, поток через клапан ламинарный.Физиологическая ре-
                гургитация.
                Клапан легочной артерии: створки не изменены, поток через клапан ламинарный. Легочная артерия d
                2.6 см, не расширена.
                Перегородки непрерывны.
        """
        emb = gigachat.get_embedding(conclusion)
        self.assertTrue(emb is None, 'embedding is not None, when it should be (too big request)')

    def test_emb(self) -> None:
        gigachat = GigaChat()

        conclusion = """
                Рентген-признаки дегенеративно-дистрофических изменений в левом голеностопном суставе. Лигаментоз
                плантарного апоневроза.
                Тендиноз ахиллова сухожилия.
                Остеопенический синдром.
        """

        emb = gigachat.get_embedding(conclusion)
        # Check if emb is a list
        self.assertTrue(isinstance(emb, Optional[list]), f'emb is not a list or None, emb: {emb}')

        if isinstance(emb, list):
            # Check if emb is not empty
            self.assertTrue(len(emb) > 0, 'emb is an empty list')

            # Check if elements of emb are floats
            self.assertTrue(all(isinstance(x, float) for x in emb), 'Not all elements in emb are floats')
