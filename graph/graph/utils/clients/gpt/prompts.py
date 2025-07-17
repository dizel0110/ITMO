"""
Module for generating static prompts from db.
=============================================

Functions:
----------
get_prompt_of_description_feature\n
get_prompt_of_desctription_extract\n
get_prompt_of_entities_classifier\n
get_prompt_of_anamnesis_groups\n
get_prompt_for_embedding_grouping_clusterization\n
get_prompt_to_decipher_abbreviation\n

Dependencies:
-------------
collections\n
django

"""

from collections import Counter

from django.conf import settings

from akcent_graph.apps.secret_settings.models import Prompt


def get_prompt_of_description_feature(name: str, meaning: str) -> str:
    """Prompts for describing a feature from a medical record."""
    prompt_example = Prompt.objects.get(name='description of personal features')
    return prompt_example.user_text.replace('{description}', meaning).replace('{symptom}', name)


def get_prompt_of_description_extract(
    anamnesis: str,
    disease: str,
    extract_sample: str,
) -> tuple[str, str]:
    """Prompts for describing extract of medical card."""
    prompt_example = Prompt.objects.get(name='description of extract from medical card')
    prompt = prompt_example.user_text.format(anamnesis=anamnesis, disease=disease, extract_sample=extract_sample)
    system_prompt = prompt_example.system_text.format(extract_sample=extract_sample)
    return prompt, system_prompt


def get_prompt_of_entities_classifier(
    daughter_entity: str,
    parent_entity: str,
) -> tuple[str, str]:
    """Prompts for classification of possible relationships for entities."""
    prompt_example = Prompt.objects.get(name='classification of possible relationships')
    prompt = prompt_example.user_text.format(daughter_entity=daughter_entity, parent_entity=parent_entity)
    system_prompt = prompt_example.system_text.format(daughter_entity=daughter_entity, parent_entity=parent_entity)
    return prompt, system_prompt


def get_prompt_of_anamnesis_groups(features: set[str]) -> str:
    """Prompt for the name of a group of medical features."""
    prompt_example = Prompt.objects.get(name='name of anamnesis groups')
    combination = Prompt.objects.get(name='combination of feature and quantity').user_text

    chains_features = [' '.join(feature.split(settings.CHAIN_SEPARATOR)) for feature in features]
    chains_counts = Counter(chains_features)
    chains_counts_for_prompt = [chain + combination + str(count) for chain, count in chains_counts.items()]
    return prompt_example.user_text.replace('{features}', str(chains_counts_for_prompt))


def get_prompt_of_diseases_entities_classifier(
    disease_name: str,
    disease_entity: str,
) -> tuple[str, str]:
    """Prompts for classification of diseases matching."""
    prompt_example = Prompt.objects.get(name='classification of diseases matching')
    prompt = prompt_example.user_text.format(disease_name=disease_name, disease_entity=disease_entity)
    system_prompt = prompt_example.system_text.format(disease_name=disease_name, disease_entity=disease_entity)
    return prompt, system_prompt


def get_prompt_for_embedding_grouping_clusterization(feature: str, chain: str) -> str:
    """Prompt to get embedding for clustering grouping true features."""
    prompt_example = Prompt.objects.get(name='for embedding of grouping clusterization')
    return prompt_example.user_text.replace('{feature}', feature).replace('{chain}', chain)


def get_prompt_to_decipher_abbreviation(phrase: str) -> str:
    """Prompt to decipher abbreviation."""
    prompt_example = Prompt.objects.get(name='decipher the phrase')
    return prompt_example.user_text.replace('{phrase}', phrase)
