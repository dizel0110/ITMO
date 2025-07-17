"""
Module for errors of YandexGPT.
===============================

Classes:
----------
DataErrorsYandexGPT

Dependencies:
-------------
enum
\nhttp

"""


import enum
from http import HTTPStatus


class DataErrorsYandexGPT(enum.Enum):
    """
    The class contains errors for quotas.
    =====================================

    Variables:
    ----------
    \n\tSYNC_MORE_THAN_ONE
    \n\tSYNC_QUOTA_PER_HOUR_IS_OVER
    \n\tRESOURCE_EXHAUSTED

    See also:
    ---------
    Needs improvement, since all the necessary errors are not known.
    The class can be extended to other errors.

    """

    SYNC_MORE_THAN_ONE = {
        'httpCode': HTTPStatus.TOO_MANY_REQUESTS.value,
        'message': 'ai.textGenerationCompletionSessionsCount.count gauge quota limit exceed: allowed 1 requests',
    }
    SYNC_QUOTA_PER_HOUR_IS_OVER = {
        'httpCode': HTTPStatus.TOO_MANY_REQUESTS.value,
        'message': 'ai.textGenerationCompletionRequestsPerHour.rate rate quota limit exceed: allowed 100 requests',
    }
    RESOURCE_EXHAUSTED = {
        'httpCode': HTTPStatus.TOO_MANY_REQUESTS.value,
    }
