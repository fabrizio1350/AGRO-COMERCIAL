from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from .models import Categoria, ItemCarrito, PagoComision, PerfilUsuario, Producto, Puesto, Pedido


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

    def test_oferta_se_publica_despues_del_pago_demo(self):
        self.client.force_login(self.vendedor)
        datos = {
            'nombre': 'Papa', 'descripcion': 'Por kilo', 'categoria': self.producto.categoria_id,
            'unidad': 'KG', 'stock': 4, 'precio': '5.00', 'precio_oferta': '4.00', 'disponible': 'on',
        }
        respuesta = self.client.post(reverse('crear_producto'), datos)
        publicado = Producto.objects.get(nombre='Papa')
        self.assertRedirects(respuesta, reverse('pagar_comision_oferta', args=[publicado.pk]))
        # Antes de pagar se ve con su precio normal, no como oferta
        self.assertTrue(publicado.oferta_pendiente_pago)
        self.assertIn(publicado, Producto.objects.publicados())
        self.assertNotIn(publicado, Producto.objects.ofertas_activas())
        pagina = self.client.get(reverse('pagar_comision_oferta', args=[publicado.pk]))
        self.assertContains(pagina, 'Tarjeta')
        self.assertContains(pagina, 'Yape o Plin')
        self.assertContains(pagina, 'S/ 2,00')
        self.assertContains(self.client.post(reverse('pagar_comision_oferta', args=[publicado.pk]), {'metodo_pago': 'BITCOIN'}),
                            'Elige si pagas con tarjeta o con QR')
        self.assertRedirects(self.client.post(reverse('pagar_comision_oferta', args=[publicado.pk]), {'metodo_pago': 'YAPE_PLIN'}),
                             reverse('panel_productor'))
        publicado.refresh_from_db()
        self.assertFalse(publicado.oferta_pendiente_pago)
        self.assertIn(publicado, Producto.objects.ofertas_activas())
        self.assertEqual(PagoComision.objects.get(producto=publicado).monto, Decimal('2.00'))
        # Pagar otra vez no crea un segundo cobro, y editar una oferta pagada no la vuelve a cobrar
        self.client.post(reverse('pagar_comision_oferta', args=[publicado.pk]), {'metodo_pago': 'TARJETA'})
        self.assertRedirects(self.client.post(reverse('editar_producto', args=[publicado.pk]), dict(datos, precio_oferta='3.50')),
                             reverse('panel_productor'))
        self.assertEqual(PagoComision.objects.filter(producto=publicado).count(), 1)
        # Quitar el precio de oferta deja el producto normal
        self.client.post(reverse('editar_producto', args=[publicado.pk]), dict(datos, precio_oferta=''))
        publicado.refresh_from_db()
        self.assertFalse(publicado.en_oferta)
        self.assertFalse(publicado.oferta_pendiente_pago)
        self.client.force_login(self.comprador)
        self.assertEqual(self.client.post(reverse('editar_producto', args=[publicado.pk]), {}).status_code, 404)


class PanelYListaTests(TestCase):
    def setUp(self):
        self.vendedor = User.objects.create_user('vende', password='clave12345')
        self.comprador = User.objects.create_user('compra', password='clave12345')
        PerfilUsuario.objects.create(usuario=self.vendedor, rol='PRODUCTOR')
        PerfilUsuario.objects.create(usuario=self.comprador, rol='COMPRADOR')
        self.producto = Producto.objects.create(
            productor=self.vendedor, nombre='Choclo', descripcion='Tierno', precio=Decimal('1.50'), stock=10,
            unidad='UNIDAD', categoria=Categoria.objects.create(nombre='Granos'),
        )

    def poner_puesto(self):
        return Puesto.objects.create(vendedor=self.vendedor, nombre='Mercado San Camilo', numero='7',
                                     latitud=Decimal('-16.4'), longitud=Decimal('-71.53'), yape_plin=True)

    def test_sin_puesto_no_se_publica(self):
        self.assertNotIn(self.producto, Producto.objects.publicados())
        self.assertEqual(self.client.get(reverse('detalle_producto', args=[self.producto.pk])).status_code, 404)
        self.poner_puesto()
        self.assertIn(self.producto, Producto.objects.publicados())
        respuesta = self.client.get(reverse('detalle_producto', args=[self.producto.pk]))
        self.assertContains(respuesta, 'Puesto 7')
        self.assertContains(respuesta, 'Yape / Plin')
        self.assertContains(respuesta, 'Cómo llegar')

    def test_vendi_resta_stock_registra_venta_y_responde_json(self):
        from .models import VentaPuesto
        self.poner_puesto()
        self.client.force_login(self.vendedor)
        url = reverse('actualizar_stock', args=[self.producto.pk])
        respuesta = self.client.post(url, {'accion': 'vendi', 'cantidad': 3}, HTTP_X_STOCK_RAPIDO='1')
        self.assertEqual(respuesta.json()['stock'], 7)
        self.assertEqual(VentaPuesto.objects.get().cantidad, 3)
        # No se puede vender mas de lo que queda
        self.assertEqual(self.client.post(url, {'accion': 'vendi', 'cantidad': 50}, HTTP_X_STOCK_RAPIDO='1').status_code, 409)
        self.client.post(url, {'accion': 'sumar', 'cantidad': 5}, HTTP_X_STOCK_RAPIDO='1')
        self.client.post(url, {'accion': 'agotado'}, HTTP_X_STOCK_RAPIDO='1')
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 0)
        self.assertIsNotNone(self.producto.stock_actualizado)
        self.assertContains(self.client.get(reverse('panel_productor')), 'S/ 4,50')

    def test_lista_del_comprador_agrupa_por_puesto_y_avisa_stock(self):
        self.poner_puesto()
        self.client.force_login(self.comprador)
        respuesta = self.client.post(reverse('agregar_al_carrito', args=[self.producto.pk]), {'cantidad': 4},
                                     HTTP_X_CARRITO_RAPIDO='1')
        self.assertEqual(respuesta.json()['total_carrito'], 1)
        pagina = self.client.get(reverse('carrito'))
        self.assertContains(pagina, 'Mercado San Camilo')
        self.assertContains(pagina, 'S/ 6,00')
        datos = self.client.get(reverse('stock_publico'), {'ids': self.producto.pk}).json()
        self.assertEqual(datos[str(self.producto.pk)]['stock'], 10)

    def test_vendedor_nuevo_va_a_marcar_su_puesto(self):
        self.client.force_login(self.vendedor)
        self.assertRedirects(self.client.get(reverse('crear_producto')), reverse('configurar_puesto'))
        self.assertContains(self.client.get(reverse('panel_productor')), 'Marcar mi puesto en el mapa')
