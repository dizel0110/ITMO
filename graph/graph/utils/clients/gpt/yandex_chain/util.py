"""
Module for setting up YandexGPT authentication.
===============================================

Classes:
----------
YException
\nYAuth :
    \n\theaders
    \n\tfrom_dict

Dependencies:
-------------
typing

"""


from typing import Optional


class YException(Exception):
    pass


class YAuth:
    """
    Authentication for YandexGPT API.
    =================================

    Methods:
    --------
    \n\t__init__
    \n\theaders
    \n\tfrom_dict

    """

    def __init__(
        self,
        folder_id: Optional[str] = None,
        api_key: Optional[str] = None,
        iam_token: Optional[str] = None,
    ) -> None:
        self.folder_id = folder_id
        self.api_key = api_key
        self.iam_token = iam_token

    @property
    def headers(self) -> Optional[dict[str, str]]:
        """Headers when accessing Yandex Cloud resources via API."""
        if self.folder_id is not None and self.api_key is not None:
            return {'Authorization': f'Api-key {self.api_key}', 'x-folder-id': self.folder_id}
        if self.folder_id is not None and self.iam_token is not None:
            return {'Authorization': f'Bearer {self.iam_token}', 'x-folder-id': self.folder_id}
        return None

    @staticmethod
    def from_dict(js: dict[str, str]) -> ...:  # type: ignore[misc]
        """Initialize API variable settings from dict."""
        if js.get('folder_id') is not None and js.get('api_key') is not None:
            return YAuth(js['folder_id'], api_key=js['api_key'])
        if js.get('iam_token') is not None:
            return YAuth(js['folder_id'], iam_token=js['iam_token'])
        raise YException(
            'Cannot create valid authentication object: you need to provide folder_id and either '
            'iam token or api_key fields',
        )
