from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from .models import Categoria, ItemCarrito, PerfilUsuario, Producto, Puesto, Pedido


class MercadoPresencialTests(TestCase):
    def setUp(self):
        self.vendedor = User.objects.create_user('puesto')
        self.comprador = User.objects.create_user('visita')
        PerfilUsuario.objects.create(usuario=self.vendedor, rol='PRODUCTOR')
        PerfilUsuario.objects.create(usuario=self.comprador)
        self.puesto = Puesto.objects.create(
            vendedor=self.vendedor, nombre='Mercado de prueba', referencia='Puesto 12',
            foto='puestos/prueba.jpg', latitud=Decimal('-16.409'), longitud=Decimal('-71.537'),
        )
        self.producto = Producto.objects.create(
            productor=self.vendedor, nombre='Palta', descripcion='Fresca', precio=Decimal('5'),
            stock=8, categoria=Categoria.objects.create(nombre='Fruta'),
        )

    def test_lista_no_reserva_y_refleja_venta_presencial(self):
        self.client.force_login(self.comprador)
        self.client.post(reverse('agregar_al_carrito', args=[self.producto.pk]), {'cantidad': 3})
        self.assertEqual(ItemCarrito.objects.get().cantidad, 3)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 8)
        self.assertFalse(Pedido.objects.exists())
        self.client.force_login(self.vendedor)
        self.client.post(reverse('actualizar_stock', args=[self.producto.pk]), {'stock_anterior': 8, 'stock': 2})
        respuesta = self.client.get(reverse('stock_publico'), {'ids': self.producto.pk})
        self.assertEqual(respuesta.json()[str(self.producto.pk)]['stock'], 2)
        self.client.post(reverse('actualizar_stock', args=[self.producto.pk]), {'stock_anterior': 8, 'stock': 7})
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 2)

    def test_comprador_no_puede_editar_stock(self):
        self.client.force_login(self.comprador)
        respuesta = self.client.post(reverse('actualizar_stock', args=[self.producto.pk]), {'stock_anterior': 8, 'stock': 0})
        self.assertEqual(respuesta.status_code, 404)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 8)

    def test_paginas_y_pasarela_desactivada(self):
        for nombre in ('inicio', 'catalogo', 'ventas_por_oferta'):
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 200)
        self.assertContains(self.client.get(reverse('detalle_producto', args=[self.producto.pk])), 'Cómo llegar')
        self.client.force_login(self.vendedor)
        for nombre in ('panel_productor', 'configurar_puesto', 'crear_producto'):
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 200)
        self.assertRedirects(self.client.post(reverse('pasarela_pago')), reverse('carrito'), fetch_redirect_response=False)
        self.assertFalse(Pedido.objects.exists())

    def test_publicar_oferta_sin_comision_y_proteger_propiedad(self):
        self.client.force_login(self.vendedor)
        respuesta = self.client.post(reverse('crear_producto'), {
            'nombre': 'Papa', 'descripcion': 'Por kilo', 'categoria': self.producto.categoria_id,
            'unidad': 'KG', 'stock': 4, 'precio': '5.00', 'precio_oferta': '4.00', 'disponible': 'on',
        })
        self.assertRedirects(respuesta, reverse('panel_productor'))
        publicado = Producto.objects.get(nombre='Papa')
        self.assertIn(publicado, Producto.objects.ofertas_activas())
        self.assertFalse(publicado.oferta_pendiente_pago)
        self.client.force_login(self.comprador)
        self.assertEqual(self.client.post(reverse('editar_producto', args=[publicado.pk]), {}).status_code, 404)
