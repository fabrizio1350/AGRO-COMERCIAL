from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve
from django.contrib.staticfiles.views import serve as servir_estatico
import re

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path('', include('mercado.urls')),
]

def _estatico(request, path):
    # Busca en static/ del proyecto y en los archivos de Django (los estilos del admin estan ahi)
    return servir_estatico(request, path, insecure=True)


if settings.SERVIR_ARCHIVOS:
    urlpatterns += [re_path(r'^static/(?P<path>.*)$', _estatico)]
    if settings.STATIC_URL != '/static/':
        urlpatterns += [
            re_path(r'^%s(?P<path>.*)$' % re.escape(settings.STATIC_URL.lstrip('/')), _estatico),
        ]
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
