import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Carga segura de variables desde el archivo .env (ignorado en Git para no filtrar claves ni contrasenas)
env_path = BASE_DIR / '.env'
if env_path.exists():
    with open(env_path, encoding='utf-8') as f:
        for linea in f:
            linea = linea.strip()
            if linea and not linea.startswith('#') and '=' in linea:
                clave, valor = linea.split('=', 1)
                os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))

# Clave secreta protegida por variable de entorno
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-agro-comercial-universidad-2026-clave-segura')

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['*']

CSRF_TRUSTED_ORIGINS = [
    'http://proyects.site',
    'https://proyects.site',
    'http://*.proyects.site',
    'https://*.proyects.site',
    'http://149.34.50.121',
    'http://149.34.50.121:8000',
]

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Permite que la ventana emergente de Google Sign-In se comunique con la pagina
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin-allow-popups'

# Aplicaciones instaladas (arquitectura monolitica MVT)
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'mercado',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'agro_comercial.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'mercado.context_processors.datos_globales_usuario',
                'mercado.context_processors.datos_del_sitio',
            ],
        },
    },
]

WSGI_APPLICATION = 'agro_comercial.wsgi.application'

# Base de datos SQLite integrada
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Algoritmo de encriptacion / hashing seguro en 3 capas (SHA-256 + SHA-512 + PBKDF2-SHA256)
PASSWORD_HASHERS = [
    'mercado.hashers.TriplePBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
]

# Validacion de contrasenas nativa de Django
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
]

LANGUAGE_CODE = 'es-pe'

TIME_ZONE = 'America/Lima'

USE_I18N = True

USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Fotos que suben los vendedores
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Rutas de redireccion para autenticacion
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'inicio'
LOGOUT_REDIRECT_URL = 'inicio'

# ==============================================================================
# COMISION DE AGROCOMERCIAL POR PUBLICAR UN PRODUCTO EN OFERTA (PAGO SIMULADO)
# ==============================================================================
# Porcentaje sobre el valor del lote en oferta (precio de oferta x stock) y monto minimo en soles
COMISION_OFERTA_PORCENTAJE = float(os.environ.get('COMISION_OFERTA_PORCENTAJE', '3'))
COMISION_OFERTA_MINIMA = float(os.environ.get('COMISION_OFERTA_MINIMA', '2.00'))

# Version de los archivos css/js: cambia sola cuando se modifican, asi el navegador no usa los viejos
def _version_estaticos():
    archivos = list((BASE_DIR / 'static' / 'css').glob('*.css')) + list((BASE_DIR / 'static' / 'js').glob('*.js'))
    return str(int(max((a.stat().st_mtime for a in archivos), default=0)))


VERSION_ESTATICOS = _version_estaticos()

# Correo de contacto que se muestra en la pagina de ayuda (opcional)
CORREO_CONTACTO = os.environ.get('CORREO_CONTACTO', '')

# Dias que dura una publicacion antes de vencer (y el maximo que puede elegir el vendedor)
PUBLICACION_DIAS_VIGENCIA = int(os.environ.get('PUBLICACION_DIAS_VIGENCIA', '30'))
PUBLICACION_DIAS_MAXIMO = int(os.environ.get('PUBLICACION_DIAS_MAXIMO', '90'))

# ==============================================================================
# CREDENCIALES DE GOOGLE OAUTH, PASARELA CULQI Y CORREO GMAIL (DESDE .env)
# ==============================================================================
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')

# Llaves de prueba (Sandbox) de Culqi
CULQI_PUBLIC_KEY = os.environ.get('CULQI_PUBLIC_KEY', 'pk_test_0000000000000000')
CULQI_SECRET_KEY = os.environ.get('CULQI_SECRET_KEY', '')

# Configuracion de envio de comprobantes por Gmail SMTP
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER or 'AgroComercial <notificaciones@agrocomercial.pe>'

if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
