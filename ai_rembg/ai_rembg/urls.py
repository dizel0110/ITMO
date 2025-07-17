"""
URL configuration for ai_photoenhancer project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = f'I_amb AI Photoenhancer Admin {settings.PRODUCT_VERSION}'
admin.site.site_title = f'I_amb AI Photoenhancer Portal {settings.PRODUCT_VERSION}'
admin.site.index_title = 'Welcome to Akcent AI Photoenhancer Portal'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('common/', include('ai_photoenhancer.apps.common.urls')),
    path('api/', include('ai_photoenhancer.apps.background_remover.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # type: ignore
