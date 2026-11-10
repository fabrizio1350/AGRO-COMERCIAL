"""Pruebas del pago real por Yape/Plin, de las dos fechas al publicar y del boton Terminar compra."""
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Categoria, CompraTerminada, ItemCarrito, Notificacion, PagoComision, PerfilUsuario, Producto, Puesto


class Base(TestCase):
    def setUp(self):
        self.vendedor = User.objects.create_user('puesto')
        self.otro_vendedor = User.objects.create_user('vecino')
        self.comprador = User.objects.create_user('visita')
        self.admin = User.objects.create_superuser('jefa', 'jefa@example.com', 'clave-larga-de-prueba')
        for usuario in (self.vendedor, self.otro_vendedor):
            PerfilUsuario.objects.create(usuario=usuario, rol='PRODUCTOR')
            Puesto.objects.create(vendedor=usuario, nombre=f'Puesto de {usuario.username}', foto='puestos/prueba.jpg',
                                  latitud=Decimal('-16.409'), longitud=Decimal('-71.537'))
        PerfilUsuario.objects.create(usuario=self.comprador)
        self.categoria = Categoria.objects.create(nombre='Fruta')
        self.oferta = self.crear(self.vendedor, 'Palta', en_oferta=True, precio_oferta=Decimal('4'), oferta_pendiente_pago=True)

    def crear(self, vendedor, nombre, **extra):
        return Producto.objects.create(productor=vendedor, nombre=nombre, descripcion='x', precio=Decimal('5'),
                                       stock=8, categoria=self.categoria, **extra)

    def pagar(self, producto, numero='12345678', tipo='PREMIUM', cliente=None, **extra):
        datos = dict({'tipo_oferta': tipo, 'numero_operacion': numero, 'nombre_pagador': 'Rosa Quispe'}, **extra)
        return (cliente or self.client).post(reverse('pagar_comision_oferta', args=[producto.pk]), datos)


class PagoPorYapeTests(Base):
    def test_el_numero_oficial_es_el_unico_y_no_se_puede_cambiar_desde_el_formulario(self):
        self.assertEqual(settings.TELEFONO_PAGOS, '900817270')
        self.client.force_login(self.vendedor)
        pagina = self.client.get(reverse('pagar_comision_oferta', args=[self.oferta.pk]))
        self.assertContains(pagina, '900 817 270')
        self.assertIn('no-store', pagina.headers['Cache-Control'])
        # Aunque alguien altere el formulario, el destino y el monto los pone el servidor
        self.pagar(self.oferta, telefono_destino='999999999', monto='0.01', estado='CONFIRMADO')
        pago = PagoComision.objects.get()
        self.assertEqual((pago.telefono_destino, pago.monto, pago.estado), ('900817270', Decimal('1.00'), 'PENDIENTE'))
        self.oferta.refresh_from_db()
        self.assertTrue(self.oferta.oferta_pendiente_pago)

    def test_un_numero_de_operacion_no_sirve_dos_veces(self):
        self.client.force_login(self.vendedor)
        self.pagar(self.oferta, '12345678')
        otra = self.crear(self.otro_vendedor, 'Mango', en_oferta=True, precio_oferta=Decimal('4'), oferta_pendiente_pago=True)
        vecino = Client()
        vecino.force_login(self.otro_vendedor)
        self.assertContains(self.pagar(otra, '1234-5678', cliente=vecino), 'ya fue registrado')
        self.assertEqual(PagoComision.objects.count(), 1)

    def test_solo_el_dueno_paga_su_oferta_y_hay_que_iniciar_sesion(self):
        url = reverse('pagar_comision_oferta', args=[self.oferta.pk])
        self.assertRedirects(self.client.get(url), f"{reverse('login')}?next={url}", fetch_redirect_response=False)
        self.client.force_login(self.otro_vendedor)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.pagar(self.oferta).status_code, 404)
        self.client.force_login(self.comprador)
        self.assertEqual(self.pagar(self.oferta).status_code, 404)
        self.assertFalse(PagoComision.objects.exists())

    def test_sin_csrf_no_se_registra_el_pago(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.vendedor)
        self.assertEqual(self.pagar(self.oferta, cliente=cliente).status_code, 403)
        self.assertFalse(PagoComision.objects.exists())

    @override_settings(PAGOS_MAXIMO_POR_DIA=2)
    def test_limite_de_envios_por_dia(self):
        self.client.force_login(self.vendedor)
        for numero in ('11111111', '22222222'):
            self.pagar(self.oferta, numero)
            PagoComision.objects.get(numero_operacion=numero).rechazar(self.admin)
        self.assertContains(self.pagar(self.oferta, '33333333'), 'Ya enviaste varios pagos hoy')
        self.assertEqual(PagoComision.objects.count(), 2)

    def test_rechazo_avisa_y_deja_enviar_otro_numero(self):
        self.client.force_login(self.vendedor)
        self.pagar(self.oferta, '11111111')
        pago = PagoComision.objects.get()
        self.assertTrue(pago.rechazar(self.admin))
        self.assertFalse(pago.confirmar(self.admin))
        self.oferta.refresh_from_db()
        self.assertTrue(self.oferta.oferta_pendiente_pago)
        self.assertTrue(Notificacion.objects.filter(usuario=self.vendedor, texto__contains='No pudimos confirmar').exists())
        self.assertContains(self.client.get(reverse('pagar_comision_oferta', args=[self.oferta.pk])), 'No pudimos confirmar tu pago anterior')
        self.pagar(self.oferta, '22222222')
        self.assertEqual(PagoComision.objects.filter(estado='PENDIENTE').count(), 1)

    def test_el_administrador_confirma_desde_el_panel_y_nadie_mas(self):
        self.client.force_login(self.vendedor)
        self.pagar(self.oferta, '11111111')
        pago = PagoComision.objects.get()
        self.assertTrue(Notificacion.objects.filter(usuario=self.admin, texto__contains='Pago por revisar').exists())
        lista = reverse('admin:mercado_pagocomision_changelist')
        accion = {'action': 'confirmar_pagos', '_selected_action': [pago.pk]}
        # El vendedor no entra al panel de administracion
        self.assertEqual(self.client.post(lista, accion).status_code, 302)
        pago.refresh_from_db()
        self.assertEqual(pago.estado, 'PENDIENTE')
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('admin:mercado_pagocomision_add')).status_code, 403)
        self.client.post(lista, accion)
        pago.refresh_from_db()
        self.assertEqual((pago.estado, pago.revisado_por), ('CONFIRMADO', self.admin))
        self.assertIn(self.oferta, Producto.objects.ofertas_premium())
        self.assertTrue(Notificacion.objects.filter(usuario=self.vendedor, texto__contains='Confirmamos tu pago').exists())


class DosFechasTests(Base):
    def datos(self, **extra):
        return dict({'nombre': 'Papa', 'descripcion': 'Por kilo', 'categoria': self.categoria.pk, 'unidad': 'KG',
                     'stock': 4, 'precio': '5.00', 'disponible': 'on'}, **extra)

    def test_formulario_muestra_las_dos_fechas(self):
        self.client.force_login(self.vendedor)
        pagina = self.client.get(reverse('crear_producto'))
        self.assertContains(pagina, '¿Desde qué día sale la oferta?')
        self.assertContains(pagina, '¿Qué día crees que se vence tu producto?')

    def test_guarda_inicio_de_oferta_y_vencimiento(self):
        hoy = timezone.localdate()
        self.client.force_login(self.vendedor)
        self.client.post(reverse('crear_producto'), self.datos(
            precio_oferta='4.00', fecha_oferta=(hoy + timedelta(days=2)).isoformat(), fecha_vence=(hoy + timedelta(days=5)).isoformat()))
        papa = Producto.objects.get(nombre='Papa')
        self.assertEqual(timezone.localtime(papa.oferta_inicio).date(), hoy + timedelta(days=2))
        self.assertEqual(timezone.localtime(papa.fecha_vencimiento).date(), hoy + timedelta(days=5))
        # Ya pagada, la oferta espera a su dia de inicio y el producto se ve con precio normal
        Producto.objects.filter(pk=papa.pk).update(oferta_pendiente_pago=False)
        papa.refresh_from_db()
        self.assertTrue(papa.oferta_programada())
        self.assertFalse(papa.oferta_activa())
        self.assertEqual(papa.precio_actual(), Decimal('5.00'))
        self.assertContains(self.client.get(reverse('editar_producto', args=[papa.pk])), (hoy + timedelta(days=5)).isoformat())

    def test_oferta_de_hoy_empieza_ya_y_el_producto_se_oculta_al_vencer(self):
        hoy = timezone.localdate()
        self.client.force_login(self.vendedor)
        self.client.post(reverse('crear_producto'), self.datos(fecha_oferta=hoy.isoformat(), fecha_vence=hoy.isoformat()))
        papa = Producto.objects.get(nombre='Papa')
        self.assertIsNone(papa.oferta_inicio)
        self.assertIn(papa, Producto.objects.publicados())
        Producto.objects.filter(pk=papa.pk).update(fecha_vencimiento=timezone.now() - timedelta(minutes=1))
        self.assertNotIn(papa, Producto.objects.publicados())

    def test_fechas_invalidas(self):
        hoy = timezone.localdate()
        self.client.force_login(self.vendedor)
        ayer, lejos = (hoy - timedelta(days=1)).isoformat(), (hoy + timedelta(days=400)).isoformat()
        self.assertContains(self.client.post(reverse('crear_producto'), self.datos(fecha_vence=ayer)), 'no puede ser un día que ya pasó')
        self.assertContains(self.client.post(reverse('crear_producto'), self.datos(fecha_vence=lejos)), 'dentro de los próximos')
        self.assertContains(self.client.post(reverse('crear_producto'), self.datos(
            precio_oferta='4.00', fecha_oferta=(hoy + timedelta(days=6)).isoformat(), fecha_vence=(hoy + timedelta(days=3)).isoformat())),
            'no puede empezar después del día en que se vence')
        self.assertFalse(Producto.objects.filter(nombre='Papa').exists())

    def test_sin_fechas_usa_las_de_siempre(self):
        self.client.force_login(self.vendedor)
        self.client.post(reverse('crear_producto'), self.datos())
        papa = Producto.objects.get(nombre='Papa')
        self.assertEqual(timezone.localtime(papa.fecha_vencimiento).date(),
                         timezone.localdate() + timedelta(days=settings.PUBLICACION_DIAS_VIGENCIA))


class TerminarCompraTests(Base):
    def setUp(self):
        super().setUp()
        self.papa = self.crear(self.vendedor, 'Papa')
        self.mango = self.crear(self.otro_vendedor, 'Mango')
        ItemCarrito.objects.create(comprador=self.comprador, producto=self.papa, cantidad=2)
        ItemCarrito.objects.create(comprador=self.comprador, producto=self.mango, cantidad=1)

    def test_terminar_compra_vacia_la_lista_y_guarda_el_historial(self):
        self.client.force_login(self.comprador)
        self.assertContains(self.client.get(reverse('carrito')), 'Terminar compra')
        respuesta = self.client.post(reverse('terminar_compra'), follow=True)
        self.assertContains(respuesta, 'Terminaste tu compra')
        self.assertContains(respuesta, 'Compras terminadas')
        self.assertContains(respuesta, 'Tu lista está vacía')
        self.assertFalse(ItemCarrito.objects.filter(comprador=self.comprador).exists())
        compra = CompraTerminada.objects.get()
        self.assertEqual((compra.total, compra.productos, compra.puestos), (Decimal('15.00'), 2, 2))
        self.assertEqual(sorted(i['nombre'] for g in compra.detalle for i in g['items']), ['Mango', 'Papa'])
        # No toca el stock: eso lo marca el vendedor en su puesto
        self.papa.refresh_from_db()
        self.assertEqual(self.papa.stock, 8)
        # Con la lista vacia no crea otra compra
        self.client.post(reverse('terminar_compra'))
        self.assertEqual(CompraTerminada.objects.count(), 1)

    def test_solo_termina_su_propia_lista_y_solo_por_post(self):
        ItemCarrito.objects.create(comprador=self.vendedor, producto=self.mango, cantidad=3)
        self.assertEqual(self.client.post(reverse('terminar_compra')).status_code, 302)
        self.assertEqual(ItemCarrito.objects.count(), 3)
        self.client.force_login(self.comprador)
        self.assertEqual(self.client.get(reverse('terminar_compra')).status_code, 405)
        self.assertEqual(ItemCarrito.objects.count(), 3)
        self.client.post(reverse('terminar_compra'))
        self.assertEqual(ItemCarrito.objects.get().comprador, self.vendedor)
        # El historial de uno no lo ve el otro
        self.client.force_login(self.vendedor)
        self.assertNotContains(self.client.get(reverse('carrito')), 'Compras terminadas')


class AjustesDeSeguridadTests(TestCase):
    def test_ajustes(self):
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, 'Lax')
        self.assertEqual(settings.X_FRAME_OPTIONS, 'DENY')
        self.assertTrue(settings.SECURE_CONTENT_TYPE_NOSNIFF)

    def test_clave_corta_no_se_acepta(self):
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            validate_password('Xk9!mq2Lp')
        validate_password('Xk9!mq2Lp7')


class VendedorYaRegistradoTests(Base):
    def test_vendedor_no_ve_empezar_a_vender(self):
        inicio = self.client.get(reverse('inicio'))
        self.assertContains(inicio, 'Empezar a vender')
        self.client.force_login(self.comprador)
        self.assertContains(self.client.get(reverse('inicio')), 'Empezar a vender')
        self.client.force_login(self.vendedor)
        for nombre in ('inicio', 'catalogo', 'panel_productor', 'carrito'):
            pagina = self.client.get(reverse(nombre))
            self.assertNotContains(pagina, 'Empezar a vender')
            self.assertNotContains(pagina, reverse('quiero_vender'))
        self.assertContains(self.client.get(reverse('inicio')), 'Ir a mi puesto')

    def test_con_puesto_marcado_nunca_pide_activarlo_otra_vez(self):
        # El perfil quedo como comprador aunque la cuenta ya tiene su puesto
        PerfilUsuario.objects.filter(usuario=self.vendedor).update(rol='COMPRADOR')
        self.client.force_login(self.vendedor)
        self.assertRedirects(self.client.get(reverse('quiero_vender')), reverse('panel_productor'), fetch_redirect_response=False)
        self.assertEqual(PerfilUsuario.objects.get(usuario=self.vendedor).rol, 'PRODUCTOR')
        self.assertEqual(self.client.get(reverse('crear_producto')).status_code, 200)
        self.assertNotContains(self.client.get(reverse('inicio')), 'Empezar a vender')

    def test_la_ubicacion_del_puesto_se_pide_una_sola_vez(self):
        nuevo = User.objects.create_user('recien')
        PerfilUsuario.objects.create(usuario=nuevo, rol='PRODUCTOR')
        self.client.force_login(nuevo)
        # Sin puesto, publicar manda a marcarlo
        self.assertRedirects(self.client.get(reverse('crear_producto')), reverse('configurar_puesto'))
        # Basta el punto del mapa y una forma de pago (sin foto) para que quede guardado
        respuesta = self.client.post(reverse('configurar_puesto'), {'latitud': '-16.403200', 'longitud': '-71.534300', 'efectivo': 'on'})
        self.assertRedirects(respuesta, reverse('crear_producto'))
        self.assertTrue(Puesto.objects.filter(vendedor=nuevo).exists())
        # Desde ahora publicar abre directo el formulario del producto, las veces que sea
        for _ in range(2):
            self.assertEqual(self.client.get(reverse('crear_producto')).status_code, 200)
        # Si falta el punto del mapa, avisa arriba que no se guardo
        otro = User.objects.create_user('sinmapa')
        PerfilUsuario.objects.create(usuario=otro, rol='PRODUCTOR')
        self.client.force_login(otro)
        self.assertContains(self.client.post(reverse('configurar_puesto'), {'efectivo': 'on'}), 'Tu puesto todavía no se guardó')


class PanelDeAdministracionTests(Base):
    def test_portada_y_lista_explican_como_confirmar(self):
        self.client.force_login(self.vendedor)
        self.pagar(self.oferta, '11111111')
        self.client.force_login(self.admin)
        portada = self.client.get(reverse('admin:index'))
        self.assertContains(portada, 'por Yape/Plin por confirmar')
        self.assertContains(portada, 'Cuentas con ofertas premium gratis')
        lista = self.client.get(reverse('admin:mercado_pagocomision_changelist'))
        self.assertContains(lista, '1 pago(s) por confirmar')
        self.assertContains(lista, 'Revisar y confirmar')
        self.assertContains(lista, 'Por confirmar')

    def test_pantalla_de_revision_confirma_o_rechaza(self):
        self.client.force_login(self.vendedor)
        self.pagar(self.oferta, '11111111')
        pago = PagoComision.objects.get()
        url = reverse('admin:mercado_pagocomision_revisar', args=[pago.pk])
        # Solo el personal entra; el vendedor no puede confirmarse su propio pago
        self.assertEqual(self.client.post(url, {'accion': 'confirmar'}).status_code, 302)
        pago.refresh_from_db()
        self.assertEqual(pago.estado, 'PENDIENTE')
        self.client.force_login(self.admin)
        pagina = self.client.get(url)
        self.assertContains(pagina, '11111111')
        self.assertContains(pagina, 'Confirmar y publicar la oferta')
        self.assertRedirects(self.client.get(reverse('admin:mercado_pagocomision_change', args=[pago.pk])), url)
        self.client.post(url, {'accion': 'confirmar'})
        pago.refresh_from_db()
        self.assertEqual(pago.estado, 'CONFIRMADO')
        self.assertIn(self.oferta, Producto.objects.ofertas_premium())
        self.assertNotContains(self.client.get(url), 'Confirmar y publicar la oferta')
        # Rechazar con mensaje para el vendedor
        otra = self.crear(self.vendedor, 'Mango', en_oferta=True, precio_oferta=Decimal('4'), oferta_pendiente_pago=True)
        self.client.force_login(self.vendedor)
        self.pagar(otra, '22222222')
        self.client.force_login(self.admin)
        segundo = PagoComision.objects.get(numero_operacion='22222222')
        self.client.post(reverse('admin:mercado_pagocomision_revisar', args=[segundo.pk]), {'accion': 'rechazar', 'motivo': 'El monto no coincide'})
        segundo.refresh_from_db()
        self.assertEqual((segundo.estado, segundo.motivo_rechazo), ('RECHAZADO', 'El monto no coincide'))

    def test_agregar_cuenta_gratis_desde_el_admin_publica_sus_ofertas(self):
        self.vendedor.email = 'puesto@gmail.com'
        self.vendedor.save()
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse('admin:mercado_cuentasinpagooferta_changelist')), 'publican ofertas premium gratis')
        self.client.post(reverse('admin:mercado_cuentasinpagooferta_add'), {'correo': 'Puesto@Gmail.com', 'nota': 'socio'})
        self.oferta.refresh_from_db()
        self.assertFalse(self.oferta.oferta_pendiente_pago)
        self.assertIn(self.oferta, Producto.objects.ofertas_premium())
