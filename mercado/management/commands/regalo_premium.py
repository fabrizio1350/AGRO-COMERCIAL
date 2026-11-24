from django.core.management.base import BaseCommand

from mercado.models import PerfilUsuario


class Command(BaseCommand):
    help = 'Vuelve a dar ofertas premium gratis a todas las cuentas (por defecto 3).'

    def add_arguments(self, parser):
        parser.add_argument('--cantidad', type=int, default=3)

    def handle(self, *args, **opciones):
        cantidad = max(0, opciones['cantidad'])
        total = PerfilUsuario.objects.update(ofertas_premium_regalo=cantidad)
        self.stdout.write(self.style.SUCCESS(f'Listo: {total} cuentas tienen {cantidad} ofertas premium gratis.'))
