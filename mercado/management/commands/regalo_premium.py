from django.core.management.base import BaseCommand

from mercado.models import PerfilUsuario


class Command(BaseCommand):
    help = 'Vuelve a dar las ofertas gratis a todas las cuentas (por defecto 1 premium y 2 normales).'

    def add_arguments(self, parser):
        parser.add_argument('--premium', type=int, default=1)
        parser.add_argument('--normal', type=int, default=2)

    def handle(self, *args, **opciones):
        premium, normal = max(0, opciones['premium']), max(0, opciones['normal'])
        total = PerfilUsuario.objects.update(ofertas_premium_regalo=premium, ofertas_normal_regalo=normal)
        self.stdout.write(self.style.SUCCESS(f'Listo: {total} cuentas tienen {premium} premium y {normal} normales gratis.'))
