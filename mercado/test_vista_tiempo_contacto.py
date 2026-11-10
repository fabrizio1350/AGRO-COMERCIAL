from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Categoria, PerfilUsuario, Producto, Puesto


class TiempoPublicacionYContactoTests(TestCase):
    def setUp(self):
        vendedor = User.objects.create_user('puesto_tiempo')
        PerfilUsuario.objects.create(usuario=vendedor, rol='PRODUCTOR')
        Puesto.objects.create(vendedor=vendedor, nombre='Mercado San Camilo', latitud=Decimal('-16.40'),
                              longitud=Decimal('-71.53'))
        self.vence = timezone.now() + timedelta(days=5, hours=2)
        self.producto = Producto.objects.create(
            productor=vendedor, nombre='Palta', descripcion='Cremosa', precio=Decimal('6'), stock=10,
            categoria=Categoria.objects.create(nombre='Frutas'), fecha_vencimiento=self.vence,
        )

    def test_tarjeta_muestra_hasta_cuando_dura_la_publicacion(self):
        respuesta = self.client.get(reverse('catalogo'))
        fecha = timezone.localtime(self.vence).strftime('%d/%m')
        self.assertContains(respuesta, 'vigencia-publicacion')
        self.assertContains(respuesta, f'Publicado hasta el {fecha}')
        self.assertContains(respuesta, 'Quedan 5 días')

    def test_detalle_muestra_la_barra_de_tiempo(self):
        respuesta = self.client.get(reverse('detalle_producto', args=[self.producto.pk]))
        self.assertContains(respuesta, 'barra-tiempo')
        self.assertContains(respuesta, 'Publicación: Quedan 5 días')

    def test_un_solo_boton_para_ingresar_o_crear_cuenta(self):
        respuesta = self.client.get(reverse('inicio'))
        self.assertContains(respuesta, 'boton-cuenta')
        self.assertNotContains(respuesta, '>Crear cuenta</a>')

    def test_contacto_abre_un_correo_redactado(self):
        respuesta = self.client.get(reverse('informacion'))
        self.assertContains(respuesta, 'mercofestas.peru@gmail.com')
        self.assertContains(respuesta, 'mailto:mercofestas.peru@gmail.com?subject=Consulta%20sobre%20MercOfertas')
        self.assertContains(respuesta, 'https://mail.google.com/mail/?view=cm')

    @override_settings(CORREO_CONTACTO='')
    def test_sin_correo_no_hay_botones(self):
        respuesta = self.client.get(reverse('informacion'))
        self.assertContains(respuesta, 'Pronto publicaremos un correo de contacto.')
