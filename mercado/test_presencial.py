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

    def test_correos_sin_pago_publican_la_oferta_directo(self):
        from io import StringIO
        from django.core.management import call_command
        from .models import CuentaSinPagoOferta
        self.vendedor.email = 'puesto@gmail.com'
        self.vendedor.save()
        self.client.force_login(self.vendedor)
        datos = {
            'nombre': 'Camote', 'descripcion': 'Morado', 'categoria': self.producto.categoria_id,
            'unidad': 'KG', 'stock': 6, 'precio': '4.00', 'precio_oferta': '3.00', 'disponible': 'on',
        }
        # Una oferta que quedo esperando el pago antes de agregar el correo
        self.client.post(reverse('crear_producto'), datos)
        pendiente = Producto.objects.get(nombre='Camote')
        self.assertTrue(pendiente.oferta_pendiente_pago)
        salida = StringIO()
        call_command('oferta_gratis', 'Puesto@Gmail.com', '--nota', 'equipo', stdout=salida)
        self.assertIn('1 oferta(s) publicadas', salida.getvalue())
        self.assertEqual(CuentaSinPagoOferta.objects.get().correo, 'puesto@gmail.com')
        pendiente.refresh_from_db()
        self.assertFalse(pendiente.oferta_pendiente_pago)
        # Las nuevas salen sin pasar por el pago y sin cobro registrado
        self.assertContains(self.client.get(reverse('crear_producto')), 'Tu cuenta publica ofertas sin pagar')
        respuesta = self.client.post(reverse('crear_producto'), dict(datos, nombre='Olluco'))
        self.assertRedirects(respuesta, reverse('panel_productor'), fetch_redirect_response=False)
        self.assertIn(Producto.objects.get(nombre='Olluco'), Producto.objects.ofertas_activas())
        self.assertFalse(PagoComision.objects.exists())
        # Al quitar el correo vuelve a pagar
        call_command('oferta_gratis', '--quitar', 'puesto@gmail.com', stdout=StringIO())
        respuesta = self.client.post(reverse('crear_producto'), dict(datos, nombre='Oca'))
        self.assertRedirects(respuesta, reverse('pagar_comision_oferta', args=[Producto.objects.get(nombre='Oca').pk]))

    def test_oferta_se_publica_despues_del_pago_demo(self):
        self.client.force_login(self.vendedor)
        self.assertNotContains(self.client.get(reverse('crear_producto')), 'S/ 2,00')
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
        self.assertContains(pagina, 'S/ 0,50')
        self.assertContains(pagina, 'S/ 1,00')
        self.assertContains(self.client.post(reverse('pagar_comision_oferta', args=[publicado.pk]),
                                             {'metodo_pago': 'BITCOIN', 'tipo_oferta': 'PREMIUM'}),
                            'Elige si pagas con tarjeta o con QR')
        self.assertContains(self.client.post(reverse('pagar_comision_oferta', args=[publicado.pk]),
                                             {'metodo_pago': 'TARJETA', 'tipo_oferta': 'GRATIS'}),
                            'Elige si tu oferta es normal o premium')
        self.assertRedirects(self.client.post(reverse('pagar_comision_oferta', args=[publicado.pk]),
                                              {'metodo_pago': 'YAPE_PLIN', 'tipo_oferta': 'PREMIUM'}),
                             reverse('panel_productor'))
        publicado.refresh_from_db()
        self.assertFalse(publicado.oferta_pendiente_pago)
        self.assertEqual(publicado.tipo_oferta, 'PREMIUM')
        self.assertIn(publicado, Producto.objects.ofertas_premium())
        self.assertEqual(PagoComision.objects.get(producto=publicado).monto, Decimal('1.00'))
        # Pagar otra vez no crea un segundo cobro, y editar una oferta pagada no la vuelve a cobrar
        self.client.post(reverse('pagar_comision_oferta', args=[publicado.pk]), {'metodo_pago': 'TARJETA', 'tipo_oferta': 'PREMIUM'})
        self.assertRedirects(self.client.post(reverse('editar_producto', args=[publicado.pk]), dict(datos, precio_oferta='3.50')),
                             reverse('panel_productor'))
        self.assertEqual(PagoComision.objects.filter(producto=publicado).count(), 1)
        # Quitar el precio de oferta deja el producto normal
        self.client.post(reverse('editar_producto', args=[publicado.pk]), dict(datos, precio_oferta=''))
        publicado.refresh_from_db()
        self.assertFalse(publicado.en_oferta)
        self.assertFalse(publicado.oferta_pendiente_pago)
        self.client.force_login(self.comprador)
        # Un comprador no puede editar: se le ofrece pasar su cuenta a vendedor
        self.assertRedirects(self.client.post(reverse('editar_producto', args=[publicado.pk]), {}), reverse('quiero_vender'))

    def test_oferta_normal_solo_en_productos_y_premium_en_todos_lados(self):
        self.client.force_login(self.vendedor)
        datos = {
            'nombre': 'Mango', 'descripcion': 'Dulce', 'categoria': self.producto.categoria_id,
            'unidad': 'KG', 'stock': 9, 'precio': '6.00', 'precio_oferta': '5.00', 'disponible': 'on',
        }
        self.client.post(reverse('crear_producto'), datos)
        mango = Producto.objects.get(nombre='Mango')
        self.client.post(reverse('pagar_comision_oferta', args=[mango.pk]), {'metodo_pago': 'TARJETA', 'tipo_oferta': 'NORMAL'})
        mango.refresh_from_db()
        self.assertEqual(mango.tipo_oferta, 'NORMAL')
        self.assertEqual(PagoComision.objects.get(producto=mango).monto, Decimal('0.50'))
        # Normal: precio de oferta y etiqueta en Productos, pero no en Ofertas ni en el carrusel
        self.assertIn(mango, Producto.objects.ofertas_activas())
        self.assertNotIn(mango, Producto.objects.ofertas_premium())
        catalogo = self.client.get(reverse('catalogo'))
        self.assertContains(catalogo, 'chip-oferta')
        self.assertNotContains(self.client.get(reverse('ventas_por_oferta')), 'Mango')
        self.assertNotContains(self.client.get(reverse('inicio')), 'carrusel-slide')
        # Pasar a premium cobra solo la diferencia
        pagina = self.client.get(reverse('pagar_comision_oferta', args=[mango.pk]))
        self.assertContains(pagina, 'Pasar a premium')
        self.client.post(reverse('pagar_comision_oferta', args=[mango.pk]), {'metodo_pago': 'TARJETA', 'tipo_oferta': 'PREMIUM'})
        mango.refresh_from_db()
        self.assertEqual(mango.tipo_oferta, 'PREMIUM')
        self.assertEqual(PagoComision.objects.filter(producto=mango).latest('fecha_pago').monto, Decimal('0.50'))
        self.assertContains(self.client.get(reverse('ventas_por_oferta')), 'Mango')
        self.assertContains(self.client.get(reverse('inicio')), 'carrusel-slide')
        # Ya premium: no hay nada mas que pagar
        self.assertRedirects(self.client.get(reverse('pagar_comision_oferta', args=[mango.pk])), reverse('panel_productor'))
        # Quitar la oferta la deja normal otra vez
        self.client.post(reverse('editar_producto', args=[mango.pk]), dict(datos, precio_oferta=''))
        mango.refresh_from_db()
        self.assertEqual(mango.tipo_oferta, 'NORMAL')

    def test_frescura_segun_dias_desde_que_llego(self):
        from datetime import timedelta
        from django.utils import timezone
        hoy = timezone.localdate()
        for dias, nivel in ((0, 'fresco'), (2, 'fresco'), (3, 'normal'), (6, 'normal'), (7, 'antiguo'), (20, 'antiguo')):
            self.producto.fecha_cosecha = hoy - timedelta(days=dias)
            self.assertEqual(self.producto.nivel_frescura(), nivel, dias)
        self.producto.save()
        self.assertContains(self.client.get(reverse('catalogo')), 'frescura-antiguo')
        # Al tocar Llego vuelve a fresco
        self.client.force_login(self.vendedor)
        self.client.post(reverse('actualizar_stock', args=[self.producto.pk]), {'accion': 'sumar', 'cantidad': 3})
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.nivel_frescura(), 'fresco')
        self.assertEqual(self.producto.texto_frescura(), 'Llegó hoy')
        # No acepta una fecha de llegada futura
        datos = {
            'nombre': 'Palta', 'descripcion': 'Fresca', 'categoria': self.producto.categoria_id, 'unidad': 'KG',
            'stock': 8, 'precio': '5.00', 'disponible': 'on', 'fecha_cosecha': (hoy + timedelta(days=1)).isoformat(),
        }
        self.assertContains(self.client.post(reverse('editar_producto', args=[self.producto.pk]), datos),
                            'no puede ser en el futuro')


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

    def test_vendi_devuelve_los_totales_del_dia_y_se_puede_quitar(self):
        from .models import VentaPuesto
        self.poner_puesto()
        self.client.force_login(self.vendedor)
        url = reverse('actualizar_stock', args=[self.producto.pk])
        datos = self.client.post(url, {'accion': 'vendi', 'cantidad': 2}, HTTP_X_STOCK_RAPIDO='1').json()
        datos = self.client.post(url, {'accion': 'vendi', 'cantidad': 1}, HTTP_X_STOCK_RAPIDO='1').json()
        self.assertEqual(datos['vendido_hoy'], '4.50')
        self.assertEqual(datos['ventas_hoy'], 2)
        self.assertEqual(datos['total_venta'], '1.50')
        self.assertContains(self.client.get(reverse('panel_productor')), 'S/ 4,50')
        # Otra cuenta no puede borrar la venta
        self.client.force_login(self.comprador)
        self.assertEqual(self.client.post(reverse('quitar_venta', args=[datos['venta_id']])).status_code, 404)
        self.client.force_login(self.vendedor)
        self.client.post(reverse('quitar_venta', args=[datos['venta_id']]))
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 8)
        self.assertEqual(VentaPuesto.objects.count(), 1)

    def test_opiniones_del_producto(self):
        from .models import ResenaProducto
        self.poner_puesto()
        url = reverse('opinar_producto', args=[self.producto.pk])
        self.client.force_login(self.comprador)
        self.assertContains(self.client.get(reverse('detalle_producto', args=[self.producto.pk])), 'Escribir al vendedor')
        self.client.post(url, {'calificacion': 9, 'comentario': 'Raro'})
        self.assertFalse(ResenaProducto.objects.exists())
        self.client.post(url, {'calificacion': 4, 'comentario': 'Choclo tierno y bien atendido'})
        self.client.post(url, {'calificacion': 5, 'comentario': 'Volví y otra vez muy bueno'})
        self.assertEqual(ResenaProducto.objects.get().calificacion, 5)
        pagina = self.client.get(reverse('detalle_producto', args=[self.producto.pk]))
        self.assertContains(pagina, 'Volví y otra vez muy bueno')
        self.assertContains(pagina, 'Actualizar mi opinión')
        # El vendedor no se califica a si mismo
        self.client.force_login(self.vendedor)
        self.client.post(url, {'calificacion': 5, 'comentario': 'El mejor'})
        self.assertEqual(ResenaProducto.objects.count(), 1)

    def test_publicar_en_otra_ubicacion_y_reusarla(self):
        from .models import UbicacionVendedor
        self.poner_puesto()
        self.client.force_login(self.vendedor)
        base = {'nombre': 'Haba', 'categoria': self.producto.categoria_id, 'unidad': 'KG', 'stock': 5,
                'precio': '4.00', 'disponible': 'on'}
        # Por defecto se vende en el puesto del inicio
        self.assertContains(self.client.get(reverse('crear_producto')), 'La que marcaste al inicio')
        sin_nombre = self.client.post(reverse('crear_producto'), dict(base, donde='nueva', nueva_latitud='-16.38', nueva_longitud='-71.55'))
        self.assertContains(sin_nombre, 'Ponle un nombre a esta ubicación')
        sin_mapa = self.client.post(reverse('crear_producto'), dict(base, donde='nueva', nueva_nombre='Feria de Cayma'))
        self.assertContains(sin_mapa, 'Marca en el mapa dónde queda la nueva ubicación')
        self.assertFalse(Producto.objects.filter(nombre='Haba').exists())
        self.client.post(reverse('crear_producto'), dict(base, donde='nueva', nueva_nombre='Feria de Cayma',
                                                         nueva_latitud='-16.380000', nueva_longitud='-71.550000'))
        feria = UbicacionVendedor.objects.get()
        haba = Producto.objects.get(nombre='Haba')
        self.assertEqual((haba.ubicacion, haba.origen), (feria, 'Feria de Cayma'))
        detalle = self.client.get(reverse('detalle_producto', args=[haba.pk]))
        self.assertContains(detalle, 'Otra ubicación de Mercado San Camilo')
        self.assertContains(detalle, '-16.380000%2C-71.550000')
        # La siguiente vez solo la elige
        self.client.post(reverse('crear_producto'), dict(base, nombre='Maca', donde=str(feria.pk)))
        self.assertEqual(Producto.objects.get(nombre='Maca').ubicacion, feria)
        self.assertEqual(UbicacionVendedor.objects.count(), 1)
        self.assertContains(self.client.get(reverse('productores')), 'Feria de Cayma')
        # El comprador ve dos paradas en su lista: el puesto y la feria
        self.client.force_login(self.comprador)
        for producto in (self.producto, haba):
            self.client.post(reverse('agregar_al_carrito', args=[producto.pk]), {'cantidad': 1})
        lista = self.client.get(reverse('carrito'))
        self.assertContains(lista, 'Feria de Cayma')
        self.assertContains(lista, 'Mercado San Camilo')
        # Otra persona no puede usar ni quitar esa ubicacion
        otro = User.objects.create_user('otro_puesto')
        PerfilUsuario.objects.create(usuario=otro, rol='PRODUCTOR')
        Puesto.objects.create(vendedor=otro, nombre='Otro mercado', latitud=Decimal('-16.4'), longitud=Decimal('-71.5'))
        self.client.force_login(otro)
        self.client.post(reverse('crear_producto'), dict(base, nombre='Ajeno', donde=str(feria.pk)))
        self.assertFalse(Producto.objects.filter(nombre='Ajeno').exists())
        self.assertEqual(self.client.post(reverse('quitar_ubicacion', args=[feria.pk])).status_code, 404)
        # Al quitarla, sus productos vuelven al puesto principal
        self.client.force_login(self.vendedor)
        self.client.post(reverse('quitar_ubicacion', args=[feria.pk]))
        haba.refresh_from_db()
        self.assertIsNone(haba.ubicacion)
        self.assertEqual(haba.origen, 'Mercado San Camilo')

    def test_datos_del_puesto_son_opcionales(self):
        puesto = self.poner_puesto()
        puesto.foto = 'puestos/prueba.jpg'
        puesto.save()
        self.client.force_login(self.vendedor)
        respuesta = self.client.post(reverse('configurar_puesto'), {
            'nombre': '', 'numero': '', 'referencia': '', 'direccion': '', 'horario': '',
            'latitud': '-16.400000', 'longitud': '-71.530000', 'efectivo': 'on',
        })
        self.assertRedirects(respuesta, reverse('panel_productor'), fetch_redirect_response=False)
        puesto.refresh_from_db()
        self.assertEqual(puesto.nombre, 'Puesto de vende')
        self.assertEqual(puesto.numero, '')
        self.assertContains(self.client.get(reverse('configurar_puesto')), 'avisoUbicacion')

    def test_vendedor_nuevo_va_a_marcar_su_puesto(self):
        self.client.force_login(self.vendedor)
        self.assertRedirects(self.client.get(reverse('crear_producto')), reverse('configurar_puesto'))
        self.assertContains(self.client.get(reverse('panel_productor')), 'Marcar mi puesto en el mapa')
