from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve
import re

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path('', include('mercado.urls')),
]

if settings.SERVIR_ARCHIVOS:
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.BASE_DIR / 'static'}),
    ]
    if settings.STATIC_URL != '/static/':
        urlpatterns += [
            re_path(r'^%s(?P<path>.*)$' % re.escape(settings.STATIC_URL.lstrip('/')), serve, {'document_root': settings.BASE_DIR / 'static'}),
        ]
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
