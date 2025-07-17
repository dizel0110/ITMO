"""Tests forsetting up YandexGPT authentication.
================================================

Classes:
----------
TestYAuthWithAPI :
    \n\ttest_headers
    \n\tcompare_auth_data
    \n\tcompare_auth_data_with_old
    \n\ttest_from_dict
TestYAuthWithIamtoken :
    \n\ttest_headers
    \n\tcompare_auth_data
    \n\tcompare_auth_data_with_old
    \n\ttest_from_dict
TestYAuthWithoutSettings :
    \n\tsetUp
    \n\ttest_headers
    \n\ttest_from_dict

"""


from django.test.testcases import SimpleTestCase

from akcent_graph.utils.clients.gpt.yandex_chain.util import YAuth, YException


class TestYAuthWithAPI(SimpleTestCase):
    """Test where an API key is used for authentication.
    ====================================================

    Methods:
    --------
    \n\tsetUp
    \n\ttest_headers
    \n\tcompare_auth_data
    \n\tcompare_auth_data_with_old
    \n\ttest_from_dict

    """

    def setUp(self) -> None:
        self.folder_id = 'sa754bdadp28oj9sinrf'
        self.api_key = 'AQXC1Yg6SEcEFN6mpwKFrzS9D-8TOwrDjIR4Y-yV'
        self.new_auth = {
            'folder_id': 'ase754bjfp28oj9sinrf',
            'api_key': 'AQVN1sSbj6UVcERgxa6mpwKFrzS9D-8TOwrDjIR4Y-yV',
        }
        self.yandex = YAuth(
            folder_id=self.folder_id,
            api_key=self.api_key,
        )

    def test_headers(self) -> None:
        self.assertEqual(
            self.yandex.headers,
            {'Authorization': f'Api-key {self.api_key}', 'x-folder-id': self.folder_id},
        )

    def compare_auth_data(self, new_yandex: YAuth) -> None:
        self.assertEqual(
            new_yandex.folder_id,
            self.new_auth['folder_id'],
        )
        self.assertEqual(
            new_yandex.api_key,
            self.new_auth['api_key'],
        )

    def compare_auth_data_with_old(self, new_yandex: YAuth) -> None:
        self.compare_auth_data(new_yandex)
        self.assertEqual(
            self.yandex.folder_id,
            self.folder_id,
        )
        self.assertEqual(
            self.yandex.api_key,
            self.api_key,
        )

    def test_from_dict(self) -> None:
        new_yandex1 = self.yandex.from_dict(self.new_auth)
        self.compare_auth_data_with_old(new_yandex1)

        new_yandex2 = YAuth.from_dict(self.new_auth)
        self.compare_auth_data(new_yandex2)


class TestYAuthWithIamtoken(SimpleTestCase):
    """Test where iam token is used for authentication.
    ===================================================

    Methods:
    --------
    \n\tsetUp
    \n\ttest_headers
    \n\tcompare_auth_data
    \n\tcompare_auth_data_with_old
    \n\ttest_from_dict

    """

    def setUp(self) -> None:
        self.folder_id = 'sa754bdadp28oj9sinrf'
        self.iam_token = (
            't1.7euelSbPyceKx87JqpuRl1qZiY-Ryi3rnpWaksrKaZqUppnLncmDnpeajZvl8_dZ'
            'NAFl-e8ENXMH_t3z9xljfmT57wQ1cwf-.-LErty1vRh4S__VEp-aDnM5huB5MEfm_'
            'Iu1u2IzNgyrn0emiWDYA6rSQXDvzjE0O3HBbUlqoDeCmXYYInzZ6Cg'
        )
        self.new_auth = {
            'folder_id': 'ase754bjfp28oj9sinrf',
            'iam_token': 't1.7euelSbPyceKx87JqpuRl1qZiY-Ryw4rnpWaskrKaFRjipnLncmDnpeajZvl8_dZNAFl-e8ENXMH_'
            't3z9xljfmT57wQ1cwf-.-LErty1vRh4S__VEp-aDnM5huB5MEfm_Iu1u2IzNgyrn0emiWDYA6rSQXDvzj'
            'E0O3HBbUlqoDeCmXYYInzZ6Cg',
        }
        self.yandex = YAuth(
            folder_id=self.folder_id,
            iam_token=self.iam_token,
        )

    def test_headers(self) -> None:
        self.assertEqual(
            self.yandex.headers,
            {'Authorization': f'Bearer {self.iam_token}', 'x-folder-id': self.folder_id},
        )

    def compare_auth_data(self, new_yandex: YAuth) -> None:
        self.assertEqual(
            new_yandex.folder_id,
            self.new_auth['folder_id'],
        )
        self.assertEqual(
            new_yandex.iam_token,
            self.new_auth['iam_token'],
        )

    def compare_auth_data_with_old(self, new_yandex: YAuth) -> None:
        self.compare_auth_data(new_yandex)
        self.assertEqual(
            self.yandex.folder_id,
            self.folder_id,
        )
        self.assertEqual(
            self.yandex.iam_token,
            self.iam_token,
        )

    def test_from_dict(self) -> None:
        new_yandex1 = self.yandex.from_dict(self.new_auth)
        self.compare_auth_data_with_old(new_yandex1)

        new_yandex2 = YAuth.from_dict(self.new_auth)
        self.compare_auth_data(new_yandex2)


class TestYAuthWithoutSettings(SimpleTestCase):
    """A test where there are no settings for authentication.
    =========================================================

    Methods:
    --------
    \n\tsetUp
    \n\ttest_headers
    \n\ttest_from_dict

    """

    def setUp(self) -> None:
        self.yandex = YAuth(
            folder_id=None,
            api_key=None,
        )

    def test_headers(self) -> None:
        self.assertEqual(
            self.yandex.headers,
            None,
        )

    def test_from_dict(self) -> None:
        self.assertRaisesRegex(
            YException,
            'Cannot create valid authentication object: you need to provide folder_id and either iam '
            'token or api_key fields',
            self.yandex.from_dict,
            {},
        )
        self.assertRaisesRegex(
            YException,
            'Cannot create valid authentication object: you need to provide folder_id and either iam '
            'token or api_key fields',
            YAuth.from_dict,
            {},
        )
