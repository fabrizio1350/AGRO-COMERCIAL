import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

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

DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
SECRET_KEY = os.environ.get('SECRET_KEY', '')
if DEBUG:
    SECRET_KEY = SECRET_KEY or 'django-insecure-solo-desarrollo-local-agro-comercial'
elif len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5 or SECRET_KEY.startswith('django-insecure-'):
    raise ImproperlyConfigured('Configura una SECRET_KEY aleatoria de al menos 50 caracteres.')

ALLOWED_HOSTS = [
    host.strip() for host in os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,[::1]').split(',')
    if host.strip()
]
if not DEBUG and (not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS):
    raise ImproperlyConfigured('Configura ALLOWED_HOSTS con los dominios del sitio.')

# REDIRIGIR_HTTPS=False si el proxy ya fuerza https y Django entra en bucle de redirecciones
SECURE_SSL_REDIRECT = not DEBUG and os.environ.get('REDIRIGIR_HTTPS', 'True').lower() == 'true'
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
if os.environ.get('TRUST_PROXY_HTTPS', '').lower() == 'true':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# Dominios con https que envian formularios, ej. https://agro.proyects.site
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()]

DATOS_DEMO_AUTOMATICOS = DEBUG and os.environ.get('DATOS_DEMO_AUTOMATICOS', '').lower() == 'true'

# True: los productos solo se ven cuando un administrador verifica el puesto del vendedor
VERIFICACION_OBLIGATORIA = os.environ.get('VERIFICACION_OBLIGATORIA', '').lower() == 'true'

# Si el servidor (nginx) no entrega /static y /media, Django los sirve con SERVIR_ARCHIVOS=True
SERVIR_ARCHIVOS = DEBUG or os.environ.get('SERVIR_ARCHIVOS', '').lower() == 'true'

# Los mapas de OpenStreetMap exigen saber desde que web se piden; solo se envia el dominio, nunca la pagina
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

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
    'mercado.seguridad.CabecerasSeguridadMiddleware',
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
        'OPTIONS': {'transaction_mode': 'IMMEDIATE'},
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
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Login normal de Django con limite de intentos: tras 5 claves equivocadas la cuenta espera 15 minutos
AUTHENTICATION_BACKENDS = ['mercado.seguridad.BackendConLimite']
LOGIN_INTENTOS_MAXIMOS = int(os.environ.get('LOGIN_INTENTOS_MAXIMOS', '5'))
LOGIN_MINUTOS_BLOQUEO = int(os.environ.get('LOGIN_MINUTOS_BLOQUEO', '15'))

# La sesion se cierra sola despues de 7 dias sin entrar
SESSION_COOKIE_AGE = 7 * 24 * 60 * 60

# Ruta del panel de administracion (cambiala en .env, ej. ADMIN_URL=gestion-agro/, para que no sea /admin/)
ADMIN_URL = os.environ.get('ADMIN_URL', 'admin/').strip('/') + '/'

LANGUAGE_CODE = 'es-pe'

TIME_ZONE = 'America/Lima'

USE_I18N = True

USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = Path(os.environ.get('STATIC_ROOT', BASE_DIR / 'staticfiles'))

# Fotos que suben los vendedores
MEDIA_URL = '/media/'
MEDIA_ROOT = Path(os.environ.get('MEDIA_ROOT', BASE_DIR / 'media'))

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Rutas de redireccion para autenticacion
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'inicio'
LOGOUT_REDIRECT_URL = 'inicio'

# ==============================================================================
# PUBLICIDAD: EL VENDEDOR PAGA PARA QUE SU PRODUCTO SALGA COMO OFERTA (PAGO DEMO)
# ==============================================================================
# Tarifa fija en soles por publicar una oferta. No es comision: las ventas en el puesto no pagan nada.
# Normal: solo la etiqueta "Oferta" en el listado de productos.
# Premium: ademas sale en el carrusel, la pagina Ofertas y el inicio.
TARIFA_OFERTA_NORMAL = float(os.environ.get('TARIFA_OFERTA_NORMAL', '0.50'))
TARIFA_OFERTA_PREMIUM = float(os.environ.get('TARIFA_OFERTA_PREMIUM', '1.00'))

# Frescura: dias desde que el producto llego al puesto
FRESCURA_DIAS_FRESCO = int(os.environ.get('FRESCURA_DIAS_FRESCO', '2'))   # 0 a 2 dias: verde
FRESCURA_DIAS_NORMAL = int(os.environ.get('FRESCURA_DIAS_NORMAL', '6'))   # 3 a 6 dias: amarillo; 7 o mas: gris

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
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')

# Llaves de prueba (Sandbox) de Culqi
CULQI_PUBLIC_KEY = os.environ.get('CULQI_PUBLIC_KEY', 'pk_test_0000000000000000')
CULQI_SECRET_KEY = os.environ.get('CULQI_SECRET_KEY', '')

# Configuracion de envio de comprobantes por Gmail SMTP
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER or 'MercOfertas <notificaciones@agrocomercial.pe>'

if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
