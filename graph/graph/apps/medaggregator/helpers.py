"""
Constant helpers module for medaggregator.
==========================================

Classes:
----------
DataImportanceFeature\n
DataAutoImportance\n
DataProtocolAttention\n
DataParentNotFound\n
DataCreatedByNeuro\n
DataRelationshipNamingByNeuro\n
DataPromptAbility\n
DataConnectAbility\n

Variables:
----------
NEO_CLASS_NAMES\n
SCORE_FOR_ERRORS

Dependencies:
-------------
enum

"""

import enum

NEO_CLASS_NAMES = [
    'NeoPatient',
    'NeoProtocol',
    'NeoBodyFluids',
    'NeoBodySystem',
    'NeoBodyStructure',
    'NeoMedServiceFeature',
    'NeoMedServiceValue',
    'NeoDisease',
    'NeoDiseaseValue',
    'NeoOrgan',
    'NeoOrganStructure',
    'NeoAnatomicalFeature',
    'NeoAnatomicalValue',
    'NeoAnomality',
    'NeoInspectionFeature',
    'NeoInspectionValue',
    'NeoMkb10_level_01',
    'NeoMkb10_level_02',
    'NeoMkb10_level_03',
    'NeoMkb10_level_04',
    'NeoMkb10_level_05',
    'NeoMkb10_level_06',
    'NeoPatientAnthropometryFeature',
    'NeoPatientAnthropometryValue',
    'NeoPatientDemographyFeature',
    'NeoPatientDemographyValue',
    'NeoProtocolFeature',
    'NeoProtocolValue',
    'NeoSymptomFeature',
    'NeoSymptomValue',
    'NeoTherapyFeature',
    'NeoTherapyValue',
    'NeoBodySystem',
]
SCORE_FOR_ERRORS = -10


class DataImportanceFeature(enum.Enum):
    """
    Constants of feature importance in medical record.
    ==================================================

    Variables:
    ----------
    FALSE_IMPORTANCE\n
    NONE_IMPORTANCE\n
    TRUE_IMPORTANCE\n
    ALL_IMPORTANCES

    """

    FALSE_IMPORTANCE = 0
    NONE_IMPORTANCE = 1
    TRUE_IMPORTANCE = 2
    ALL_IMPORTANCES = -1


class DataAutoImportance(enum.Enum):
    """
    Constants for automatic marking of nodes.
    =========================================

    Variables:
    ----------
    NODE_TRUE_IMPORTANCE\n
    NODE_FALSE_IMPORTANCE\n
    NODE_IF_VALUE_NOT_FALSE\n
    FALSE_SINGLE_NODE

    """

    NODE_TRUE_IMPORTANCE: list[str] = []
    NODE_FALSE_IMPORTANCE: list[str] = [
        'NeoMedServiceFeature',
        'NeoPatientAnthropometryFeature',
        'NeoPatientDemographyFeature',
        'NeoPatientDemographyValue',
        'NeoProtocolFeature',
        'NeoProtocolValue',
        'NeoTherapyFeature',
        'NeoTherapyValue',
    ]
    NODE_IF_VALUE_NOT_FALSE: list[str] = [
        'NeoBodyFluids',
        'NeoBodyStructure',
        'NeoOrgan',
        'NeoInspectionFeature',
        'NeoOrganStructure',
    ]
    FALSE_SINGLE_NODE: list[str] = [
        'NeoBodyFluids',
        'NeoBodySystem',
        'NeoBodyStructure',
        'NeoMedServiceFeature',
        'NeoMedServiceValue',
        'NeoOrgan',
        'NeoOrganStructure',
        'NeoAnatomicalFeature',
        'NeoAnatomicalValue',
        'NeoInspectionFeature',
        'NeoInspectionValue',
        'NeoPatientAnthropometryFeature',
        'NeoPatientAnthropometryValue',
        'NeoPatientDemographyFeature',
        'NeoPatientDemographyValue',
        'NeoTherapyFeature',
        'NeoTherapyValue',
        'NeoBodySystem',
    ]


class DataProtocolAttention(enum.Enum):
    """
    Constants for attention of protocols.
    =====================================

    Variables:
    ----------
    FALSE\n
    NONE\n
    NONE_FIRST\n
    TRUE_WITH_NONE\n
    TRUE\n
    ALL

    """

    FALSE = 0
    NONE = 1
    NONE_FIRST = 2
    TRUE_WITH_NONE = 3
    TRUE = 4
    ALL = 5


class DataParentNotFound(enum.Enum):
    """
    Constants for parent not found definition.
    ==========================================

    Variables:
    ----------
    FOUND_PARENT\n
    NONE_PARENT\n
    NOT_FOUND_PARENT

    """

    FOUND_PARENT = 0
    NONE_PARENT = 1
    NOT_FOUND_PARENT = 2


class DataCreatedByNeuro(enum.Enum):
    """
    Constants for key created by neuro in relationships.
    ====================================================

    Variables:
    ----------
    FALSE      if parent not found case\n
    NONE       not defined value for parent_not_found value\n
    TRUE       if parent not found before NeoSpider task\n
    SPIDER_1   if NeoSpider find parents or children enteties

    """

    FALSE = 0
    NONE = 1
    TRUE = 2
    SPIDER_1 = 3


class DataRelationshipNamingByNeuro(enum.Enum):
    """
    Constants for relationships naming created by neuro.
    ====================================================

    Variables:
    ----------
    NEURO_NAME      general relationship naming created by neuro\n
    SPIDER_1_NAME   relationship naming created by neuro during NeoSpider task

    """

    NEURO_NAME = 'CREATED_BY_NEURO'
    SPIDER_1_NAME = 'CREATED_BY_SPIDER_1'


class DataPromptAbility(enum.Enum):
    """
    Constants for prompt ability.
    =============================

    Variables:
    ----------
    PROMPT_CHECK_FALSE  switch on step\n
    PROMPT_CHECK_TRUE   switch off step
    """

    PROMPT_CHECK_FALSE = False
    PROMPT_CHECK_TRUE = True


class DataConnectAbility(enum.Enum):
    """
    Constants to switch connect ability.
    ====================================

    Variables:
    ----------
    SWITCH_OFF  no connect\n
    SWITCH_ON   connect ability on
    """

    SWITCH_OFF = '0'
    SWITCH_ON = '1'
