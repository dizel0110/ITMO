from django.contrib import admin

from .models import AbbreviatedPhrase, AdditionalFeatureClassifier, DescriptionFeature, FeatureClassifier


@admin.register(FeatureClassifier)
class FeatureClassifierAdmin(admin.ModelAdmin):
    list_display = [
        'feature',
    ]


@admin.register(AdditionalFeatureClassifier)
class AdditionalClassifierAdmin(admin.ModelAdmin):
    list_display = [
        'feature',
        'additional_feature',
    ]


@admin.register(DescriptionFeature)
class DescriptionFeatureAdmin(admin.ModelAdmin):
    search_fields = [
        'name',
        'value',
    ]
    list_display = [
        'id',
        'name',
        'value',
    ]


@admin.register(AbbreviatedPhrase)
class AbbreviatedPhraseAdmin(admin.ModelAdmin):
    search_fields = [
        'abbreviated_phrase',
        'decrypted_phrase',
    ]
    list_display = [
        'abbreviated_phrase',
        'decrypted_phrase',
    ]
