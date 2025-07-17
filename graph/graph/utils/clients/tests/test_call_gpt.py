"""
Module for testing of GPT in call gpt.
======================================

Classes:
----------
TestGPT :
    \n\ttest_make_request_async
    \n\ttest_make_request_sync
    \n\ttest_make_request_unknown

Dependencies:
-------------
django

"""

from django.core.cache import cache
from django.test.testcases import TestCase

from akcent_graph.utils.clients.gpt.call_gpt import GPT


class TestGPT(TestCase):
    """
    Tests for akcent_graph.utils.clients.gpt.call_gpt.py
    =================================================

    Methods:
    --------
    \n\tsetUp
    \n\ttest_make_request_async
    \n\ttest_make_request_sync
    \n\ttest_make_request_unknown

    """

    def setUp(self) -> None:
        self.prompt = (
            'Мне врач дал заключение. Напиши либо True либо False. True, если нужна врачебная помощь в '
            'случае,  представляющем угрозу здоровью в течение месяца. False если я выздоровлю за '
            'ближайший месяц.'
        )
        self.system_prompt = (
            'Ты профессор медицины. Нужно дать бинарное описание заключения.\nЗаключение: 33 года. '
            'жалоба на боль внизу живота в течение 25 дней.Отмечает повышение температуры 37,6. '
            'в *ДАТА*. В настоящее время боли внизу живота, периодически субфебрильная температура.'
        )

    def test_make_request_async(self) -> None:
        gpt = GPT()
        answer = gpt.make_request(
            self.prompt,
            self.system_prompt,
        )
        async_quota_per_hour = cache.get('async_quota_per_hour')
        self.assertIsInstance(answer, str)
        self.assertIsInstance(async_quota_per_hour, int)

    def test_make_request_sync(self) -> None:
        gpt = GPT('lite', 'sync')
        answer = gpt.make_request(
            self.prompt,
            self.system_prompt,
        )
        async_quota_per_hour = cache.get('sync_quota_per_hour')
        simultaneous_generations = cache.get('simultaneous_generations')
        self.assertIsInstance(answer, str)
        self.assertIsInstance(async_quota_per_hour, int)
        self.assertIsInstance(simultaneous_generations, int)

    def test_make_request_unknown(self) -> None:
        gpt = GPT('lite', 'unknow')
        answer = gpt.make_request(
            self.prompt,
            self.system_prompt,
        )
        self.assertEqual(answer, '')
