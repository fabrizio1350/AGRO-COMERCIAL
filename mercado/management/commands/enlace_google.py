from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.urls import reverse

from mercado.views import HORAS_ENLACE_GOOGLE, crear_enlace_google


class Command(BaseCommand):
    help = ('Crea un enlace de 1 hora para que una cuenta antigua (sin vincular) pueda entrar con Google. '
            'La persona debe elegir en Google el mismo correo que tiene su cuenta.')

    def add_arguments(self, parser):
        parser.add_argument('cuenta', help='Usuario o correo de la cuenta')
        parser.add_argument('--sitio', default='', help='Dirección de la web, ej. https://agro.proyects.site')

    def handle(self, *args, **opciones):
        cuenta = opciones['cuenta'].strip()
        usuarios = list(User.objects.filter(Q(username=cuenta) | Q(email__iexact=cuenta)))
        if not usuarios:
            raise CommandError(f'No hay ninguna cuenta con el usuario o correo "{cuenta}".')
        if len(usuarios) > 1:
            nombres = ', '.join(u.username for u in usuarios)
            raise CommandError(f'Ese correo lo usan varias cuentas ({nombres}). Escribe el usuario exacto.')
        usuario = usuarios[0]
        if not usuario.email:
            raise CommandError('La cuenta no tiene correo. Agrégalo en /admin/ antes de crear el enlace.')
        if getattr(getattr(usuario, 'perfil', None), 'google_sub', None):
            raise CommandError('Esa cuenta ya está vinculada con Google.')

        sitio = opciones['sitio'].rstrip('/')
        if not sitio:
            hosts = [h for h in settings.ALLOWED_HOSTS if h not in ('localhost', '127.0.0.1', '[::1]') and not h.startswith('.')]
            sitio = f'https://{hosts[0]}' if hosts else 'http://127.0.0.1:8000'
        enlace = sitio + reverse('enlace_google', args=[crear_enlace_google(usuario)])
        self.stdout.write(self.style.SUCCESS(f'Enlace para {usuario.username} ({usuario.email}), válido por {HORAS_ENLACE_GOOGLE} hora:'))
        self.stdout.write(enlace)
