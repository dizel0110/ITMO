"""
Module for creating feature descriptions.
=========================================

Classes:
----------
DescriptionFunctionProcessing :
    get_description_feature\n
    get_description_with_abbreviation\n

Dependencies:
-------------
django\n
logging\n

"""

import logging

from django.db.utils import IntegrityError

from akcent_graph.apps.feature_classifier.models import AbbreviatedPhrase, DescriptionFeature
from akcent_graph.utils.clients.gpt.call_gpt import GPT
from akcent_graph.utils.clients.gpt.prompts import (
    get_prompt_of_description_feature,
    get_prompt_to_decipher_abbreviation,
)

logger = logging.getLogger(__name__)


class DescriptionFunctionProcessing:
    """
    Get descriptions for features from GPT.
    =======================================

    Methods:
    --------
        get_description_feature\n
        get_description_with_abbreviation\n

    """

    def __init__(
        self,
        model_type_gpt: str = 'lite',
        request_type_gpt: str = 'sync',
        max_tokens_gpt: int = 512,
    ):
        self.gpt = GPT(
            model_type=model_type_gpt,
            request_type=request_type_gpt,
            max_tokens=max_tokens_gpt,
        )

    def get_description_feature(self, name: str, meaning: str) -> str:
        """Get a paraphrase of the feature about the symptom property from gpt."""
        try:
            description_db = DescriptionFeature.objects.get(
                name=name,
                value=meaning,
            )
            return description_db.gpt_description
        except DescriptionFeature.DoesNotExist:
            user_prompt = get_prompt_of_description_feature(
                name,
                meaning,
            )

            description = self.gpt.make_request(user_prompt)
            if description:
                clear_description = description.replace('*', '')
                try:
                    DescriptionFeature.objects.create(
                        name=name,
                        value=meaning,
                        gpt_description=clear_description,
                    )
                except IntegrityError:
                    pass
                return clear_description
            logger.warning('YandexGPT not return description.')
            return description

    def get_description_with_abbreviation(self, phrase: str) -> str:
        """Decoding medical abbreviations."""
        try:
            description_db = AbbreviatedPhrase.objects.get(
                abbreviated_phrase=phrase,
            )
            return description_db.decrypted_phrase
        except AbbreviatedPhrase.DoesNotExist:
            prompt = get_prompt_to_decipher_abbreviation(phrase)
            decrypted_phrase = self.gpt.make_request(prompt)
            if decrypted_phrase:
                try:
                    AbbreviatedPhrase.objects.create(
                        abbreviated_phrase=phrase,
                        decrypted_phrase=decrypted_phrase,
                    )
                except IntegrityError:
                    pass
                return decrypted_phrase
            logger.warning('YandexGPT not return decrypted phrase.')
            return phrase
