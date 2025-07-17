from django.contrib import admin

from ai_photoenhancer.apps.background_remover.models import ImageInfo


@admin.register(ImageInfo)
class ImageInfoAdmin(admin.ModelAdmin):
    list_display = ['filename', 'user_id', 'created_at', 'processed_at']
    readonly_fields = ['filename', 'created_at']
    ordering = ['-created_at']
