"""Protecciones generales de la web: limite de intentos de login, cabeceras de seguridad
y revision de las fotos que suben los usuarios."""
import logging
import time
import uuid

from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.core.cache import cache
from django.dispatch import receiver

INTENTOS_MAXIMOS = getattr(settings, 'LOGIN_INTENTOS_MAXIMOS', 5)
MINUTOS_BLOQUEO = getattr(settings, 'LOGIN_MINUTOS_BLOQUEO', 15)

registro_admin = logging.getLogger('mercado.admin')


# ---------------------------------------------------------------- intentos de login

def _clave_intentos(usuario):
    return f'login-fallidos:{(usuario or "").strip().lower()[:150]}'


def login_bloqueado(usuario):
    return cache.get(_clave_intentos(usuario), 0) >= INTENTOS_MAXIMOS


class BackendConLimite(ModelBackend):
    """Igual que el login normal de Django, pero despues de varios intentos fallidos
    la cuenta no acepta contraseñas durante unos minutos (frena a quien prueba claves)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get('username')
        if login_bloqueado(username):
            return None
        return super().authenticate(request, username=username, password=password, **kwargs)


@receiver(user_login_failed)
def contar_intento_fallido(sender, credentials, **kwargs):
    clave = _clave_intentos(credentials.get('username'))
    if cache.add(clave, 1, MINUTOS_BLOQUEO * 60):
        return
    try:
        cache.incr(clave)
    except ValueError:
        cache.set(clave, 1, MINUTOS_BLOQUEO * 60)


@receiver(user_logged_in)
def limpiar_intentos(sender, user, request=None, **kwargs):
    cache.delete(_clave_intentos(user.get_username()))
    if request is not None and request.path.startswith('/' + settings.ADMIN_URL):
        registro_admin.info('Ingreso al admin: %s desde %s', user.get_username(), _ip(request))


def _ip(request):
    return request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR', '?')


@receiver(user_login_failed)
def avisar_fallo_admin(sender, credentials, request=None, **kwargs):
    if request is not None and request.path.startswith('/' + settings.ADMIN_URL):
        registro_admin.warning('Contraseña incorrecta en el admin para "%s" desde %s',
                               (credentials.get('username') or '')[:150], _ip(request))


# ---------------------------------------------------------------- cabeceras

class CabecerasSeguridadMiddleware:
    """Agrega cabeceras que el navegador usa para bloquear ataques comunes:
    nadie puede meter la web en un iframe, ni cargar plugins, ni mandar formularios a otro sitio."""

    def __init__(self, get_response):
        self.get_response = get_response
        politica = [
            "object-src 'none'",
            "base-uri 'self'",
            "frame-ancestors 'none'",
            # Mercado Pago: al tocar "Pagar" el formulario redirige a su pagina de pago
            "form-action 'self' https://accounts.google.com https://www.mercadopago.com.pe https://*.mercadopago.com.pe "
            "https://www.mercadopago.com https://*.mercadopago.com https://*.mercadolibre.com",
        ]
        if not settings.DEBUG:
            politica.append('upgrade-insecure-requests')
        self.csp = '; '.join(politica)

    def __call__(self, request):
        respuesta = self.get_response(request)
        respuesta.headers.setdefault('Content-Security-Policy', self.csp)
        respuesta.headers.setdefault(
            'Permissions-Policy', 'camera=(), microphone=(), payment=(), usb=(), geolocation=(self)')
        return respuesta


class ProteccionAdminMiddleware:
    """Cuida el panel de administracion:
    - si el administrador deja el panel quieto un rato, se cierra su sesion;
    - el navegador no guarda copias de las paginas del panel (nadie las ve con "atras");
    - los buscadores no lo muestran en Google."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.prefijo = '/' + settings.ADMIN_URL
        self.segundos = getattr(settings, 'ADMIN_MINUTOS_INACTIVO', 30) * 60

    def __call__(self, request):
        if not request.path.startswith(self.prefijo):
            return self.get_response(request)

        usuario = getattr(request, 'user', None)
        if usuario is not None and usuario.is_authenticated and usuario.is_staff:
            ahora = int(time.time())
            ultimo = request.session.get('admin_ultimo_movimiento')
            if ultimo and ahora - ultimo > self.segundos:
                registro_admin.info('Sesion del admin cerrada por inactividad: %s', usuario.get_username())
                logout(request)
            else:
                request.session['admin_ultimo_movimiento'] = ahora

        respuesta = self.get_response(request)
        respuesta.headers['Cache-Control'] = 'no-store, private'
        respuesta.headers['X-Robots-Tag'] = 'noindex, nofollow'
        return respuesta


# ---------------------------------------------------------------- fotos

def tipo_de_imagen(archivo):
    """Mira los primeros bytes del archivo (no el nombre) y dice si es JPG, PNG o WEBP."""
    cabecera = archivo.read(12)
    archivo.seek(0)
    if cabecera.startswith(b'\xff\xd8\xff'):
        return 'jpg'
    if cabecera.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if cabecera[:4] == b'RIFF' and cabecera[8:12] == b'WEBP':
        return 'webp'
    return None


def renombrar_imagen(archivo, extension):
    """Guarda la foto con un nombre al azar y la extension real, asi nadie puede subir
    un archivo .html o .svg disfrazado de foto."""
    archivo.name = f'{uuid.uuid4().hex}.{extension}'
    return archivo
