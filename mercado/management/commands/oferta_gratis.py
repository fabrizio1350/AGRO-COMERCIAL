from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email

from mercado.models import CuentaSinPagoOferta, Producto


class Command(BaseCommand):
    help = ('Maneja los correos que publican ofertas sin pagar la publicidad. '
            'Ej: oferta_gratis ana@gmail.com luis@gmail.com  |  oferta_gratis --quitar ana@gmail.com  |  oferta_gratis --lista')

    def add_arguments(self, parser):
        parser.add_argument('correos', nargs='*', help='Correos de las cuentas')
        parser.add_argument('--quitar', action='store_true', help='Quita los correos de la lista (vuelven a pagar)')
        parser.add_argument('--lista', action='store_true', help='Muestra los correos que hoy no pagan')
        parser.add_argument('--nota', default='', help='Nota para recordar por qué no pagan')

    def handle(self, *args, **opciones):
        correos = [c.strip().lower() for c in opciones['correos'] if c.strip()]
        if opciones['lista'] or not correos:
            self.mostrar_lista()
            return
        for correo in correos:
            try:
                validate_email(correo)
            except ValidationError:
                raise CommandError(f'"{correo}" no es un correo válido.')
        for correo in correos:
            if opciones['quitar']:
                borrados, _ = CuentaSinPagoOferta.objects.filter(correo__iexact=correo).delete()
                self.stdout.write(f'{correo}: {"quitado, vuelve a pagar" if borrados else "no estaba en la lista"}')
                continue
            _, nuevo = CuentaSinPagoOferta.objects.get_or_create(correo=correo, defaults={'nota': opciones['nota'][:120]})
            usuario = User.objects.filter(email__iexact=correo).first()
            # Si ya tenia ofertas esperando el pago, se publican de una vez
            publicadas = Producto.objects.filter(productor=usuario, en_oferta=True, oferta_pendiente_pago=True).update(
                oferta_pendiente_pago=False, tipo_oferta='PREMIUM') if usuario else 0
            estado = 'agregado' if nuevo else 'ya estaba'
            cuenta = f'cuenta {usuario.username}' if usuario else 'aún nadie se registró con ese correo'
            extra = f', {publicadas} oferta(s) publicadas' if publicadas else ''
            self.stdout.write(self.style.SUCCESS(f'{correo}: {estado} ({cuenta}{extra})'))

    def mostrar_lista(self):
        filas = list(CuentaSinPagoOferta.objects.all())
        if not filas:
            self.stdout.write('Todavía no hay correos sin pago. Agrega uno: manage.py oferta_gratis correo@gmail.com')
            return
        for fila in filas:
            self.stdout.write(f'{fila.correo}{" · " + fila.nota if fila.nota else ""}')
