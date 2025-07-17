"""
Module for help with constant with GPT.
=======================================

Classes:
----------
TemperatureYandexGPT
\nNameBioGender

Dependencies:
-------------
enum

"""


import enum


class TemperatureYandexGPT(enum.Enum):
    """
    Frequent variables for GPT temperature.
    =======================================

    Variables:
    ----------
    \n\tSIMPLE_RESPONSE
    \n\tDEFAULT
    \n\tCREATIVE_RANDOM_RESPONSE

    See also:
    ---------
    Affects creativity and randomness of responses.
    Should be a double number between 0 (inclusive)
    and 1 (inclusive). Lower values produce more
    straightforward responses, while higher values
    lead to increased creativity and randomness.
    Default temperature: 0.6.

    """

    SIMPLE_RESPONSE = 0.0
    DEFAULT = 0.6
    CREATIVE_RANDOM_RESPONSE = 1.0


class NameBioGender(enum.Enum):
    """
    Gender variables for GPT and semantic search.
    =============================================

    Variables:
    ----------
    \n\tMALE
    \n\tFEMALE
    \n\tBOY
    \n\tGIRL

    """

    MALE = 'мужчина'
    FEMALE = 'женщина'
    BOY = 'мальчик'
    GIRL = 'девочка'
