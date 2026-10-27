from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
import shutil
import tempfile
from django.urls import reverse
from django.utils import timezone
from .forms import ProductoForm
from .models import Categoria, PerfilUsuario, Producto, Conversacion, Mensaje, Notificacion, Favorito, OfertaNegociacion


class PruebasOfertasYVencimiento(TestCase):
    def setUp(self):
        self.vendedor = User.objects.create_user('vendedor', password='clave12345', first_name='Ana')
        PerfilUsuario.objects.create(usuario=self.vendedor, rol='PRODUCTOR')
        self.categoria = Categoria.objects.create(nombre='Frutas de Estación')

    def crear(self, **datos):
        valores = dict(
            productor=self.vendedor, categoria=self.categoria, nombre='Palta', descripcion='Palta fuerte',
            precio=Decimal('10.00'), stock=50, origen='Cayma, Arequipa',
        )
        valores.update(datos)
        return Producto.objects.create(**valores)

    def test_publicacion_vencida_no_se_muestra(self):
        vencido = self.crear(fecha_vencimiento=timezone.now() - timedelta(minutes=1))
        vigente = self.crear(nombre='Papa')
        publicados = list(Producto.objects.publicados())
        self.assertNotIn(vencido, publicados)
        self.assertIn(vigente, publicados)
        self.assertTrue(vencido.esta_vencida())

    def test_oferta_vencida_vuelve_al_precio_normal(self):
        prod = self.crear(en_oferta=True, precio_oferta=Decimal('8.00'),
                          oferta_inicio=timezone.now() - timedelta(days=3),
                          oferta_fin=timezone.now() - timedelta(hours=1))
        self.assertFalse(prod.oferta_activa())
        self.assertEqual(prod.precio_actual(), Decimal('10.00'))
        self.assertNotIn(prod, Producto.objects.ofertas_activas())

    def test_oferta_programada_aun_no_rige(self):
        prod = self.crear(en_oferta=True, precio_oferta=Decimal('8.00'),
                          oferta_inicio=timezone.now() + timedelta(days=1),
                          oferta_fin=timezone.now() + timedelta(days=5))
        self.assertFalse(prod.oferta_activa())
        self.assertTrue(prod.oferta_programada())

    def test_oferta_sin_pagar_no_aparece(self):
        prod = self.crear(en_oferta=True, precio_oferta=Decimal('8.00'), oferta_pendiente_pago=True)
        self.assertNotIn(prod, Producto.objects.ofertas_activas())

    def test_oferta_vigente_calcula_descuento_y_barra(self):
        prod = self.crear(en_oferta=True, precio_oferta=Decimal('7.50'),
                          oferta_inicio=timezone.now() - timedelta(days=1),
                          oferta_fin=timezone.now() + timedelta(days=3))
        self.assertTrue(prod.oferta_activa())
        self.assertEqual(prod.porcentaje_descuento(), 25)
        self.assertEqual(prod.ahorro(), Decimal('2.50'))
        self.assertEqual(prod.fecha_limite(), prod.oferta_fin)
        self.assertEqual(prod.porcentaje_tiempo_restante(), 75)

    def datos_form(self, **extra):
        hoy = timezone.localdate()
        datos = {
            'categoria': self.categoria.id, 'nombre': 'Palta', 'fecha_cosecha': hoy.isoformat(),
            'origen': 'Cayma, Arequipa', 'descripcion': 'x', 'precio': '10', 'unidad': 'KG',
            'stock': '10', 'minimo_compra': '1', 'disponible': 'on',
            'vence_el': (hoy + timedelta(days=20)).isoformat(),
        }
        datos.update(extra)
        return datos

    def test_form_rechaza_oferta_mayor_al_precio(self):
        hoy = timezone.localdate()
        form = ProductoForm(self.datos_form(en_oferta='on', precio_oferta='12', oferta_hasta=(hoy + timedelta(days=5)).isoformat()))
        self.assertFalse(form.is_valid())
        self.assertIn('precio_oferta', form.errors)

    def test_form_rechaza_oferta_ya_vencida_o_mas_larga_que_publicacion(self):
        hoy = timezone.localdate()
        form = ProductoForm(self.datos_form(en_oferta='on', precio_oferta='8', oferta_hasta=(hoy - timedelta(days=1)).isoformat()))
        self.assertIn('oferta_hasta', form.errors)
        form = ProductoForm(self.datos_form(en_oferta='on', precio_oferta='8', oferta_hasta=(hoy + timedelta(days=40)).isoformat()))
        self.assertIn('oferta_hasta', form.errors)

    def test_form_guarda_fechas(self):
        hoy = timezone.localdate()
        form = ProductoForm(self.datos_form(en_oferta='on', precio_oferta='8', oferta_hasta=(hoy + timedelta(days=5)).isoformat()))
        self.assertTrue(form.is_valid(), form.errors)
        prod = form.save(commit=False)
        self.assertEqual(timezone.localtime(prod.fecha_vencimiento).date(), hoy + timedelta(days=20))
        self.assertEqual(timezone.localtime(prod.oferta_fin).date(), hoy + timedelta(days=5))

    def test_login_lleva_a_ofertas(self):
        respuesta = self.client.post(reverse('login'), {'username': 'vendedor', 'password': 'clave12345'})
        self.assertRedirects(respuesta, reverse('ventas_por_oferta'), fetch_redirect_response=False)

    def test_registro_lleva_a_ofertas(self):
        respuesta = self.client.post(reverse('registro'), {
            'username': 'nuevo', 'first_name': 'Luis', 'last_name': 'Quispe', 'email': 'luis@example.com',
            'rol': 'COMPRADOR', 'password1': 'ClaveSegura2026!', 'password2': 'ClaveSegura2026!',
        })
        self.assertRedirects(respuesta, reverse('ventas_por_oferta'), fetch_redirect_response=False)

    def test_paginas_con_carrusel_cargan(self):
        self.crear(en_oferta=True, precio_oferta=Decimal('8.00'), oferta_fin=timezone.now() + timedelta(days=2))
        self.client.login(username='vendedor', password='clave12345')
        for nombre in ('ventas_por_oferta', 'catalogo'):
            respuesta = self.client.get(reverse(nombre))
            self.assertContains(respuesta, 'Ofertas destacadas del campo')
            self.assertContains(respuesta, 'barra-tiempo')
        respuesta = self.client.get(reverse('catalogo'), {'precio_max': '9', 'ofertas': '1', 'ubicacion': 'Cayma, Arequipa'})
        self.assertContains(respuesta, '1 producto encontrado')

    def test_renovar_publicacion_vencida(self):
        prod = self.crear(fecha_vencimiento=timezone.now() - timedelta(days=1))
        self.client.login(username='vendedor', password='clave12345')
        self.client.post(reverse('renovar_producto', args=[prod.id]))
        prod.refresh_from_db()
        self.assertFalse(prod.esta_vencida())

    def test_publicar_oferta_pagar_comision_y_aparece(self):
        hoy = timezone.localdate()
        self.client.login(username='vendedor', password='clave12345')
        respuesta = self.client.post(reverse('crear_producto'), self.datos_form(
            en_oferta='on', precio_oferta='8', oferta_hasta=(hoy + timedelta(days=5)).isoformat()))
        prod = Producto.objects.get(nombre='Palta')
        self.assertRedirects(respuesta, reverse('pagar_comision_oferta', args=[prod.id]), fetch_redirect_response=False)
        self.assertNotIn(prod, Producto.objects.ofertas_activas())
        self.client.post(reverse('pagar_comision_oferta', args=[prod.id]), {'metodo_pago': 'YAPE_PLIN'})
        self.assertIn(prod, Producto.objects.ofertas_activas())
        respuesta = self.client.get(reverse('ventas_por_oferta'))
        self.assertContains(respuesta, 'Palta')


class PruebasChatYFavoritos(TestCase):
    def setUp(self):
        self.vendedor = User.objects.create_user('vendedor', password='clave12345', first_name='Ana')
        PerfilUsuario.objects.create(usuario=self.vendedor, rol='PRODUCTOR')
        self.comprador = User.objects.create_user('comprador', password='clave12345', first_name='Luis')
        PerfilUsuario.objects.create(usuario=self.comprador, rol='COMPRADOR')
        self.intruso = User.objects.create_user('intruso', password='clave12345')
        PerfilUsuario.objects.create(usuario=self.intruso, rol='COMPRADOR')
        self.producto = Producto.objects.create(
            productor=self.vendedor, nombre='Papa', descripcion='Papa amarilla',
            precio=Decimal('3.00'), stock=500, origen='Chiguata, Arequipa',
        )

    def abrir_chat(self):
        self.client.login(username='comprador', password='clave12345')
        self.client.post(reverse('iniciar_chat', args=[self.producto.id]), {'texto': 'Hola, ¿hay 100 kg?'})
        return Conversacion.objects.get(producto=self.producto, comprador=self.comprador)

    def test_comprador_abre_chat_y_vendedor_recibe_aviso(self):
        chat = self.abrir_chat()
        self.assertEqual(chat.vendedor, self.vendedor)
        self.assertEqual(chat.mensajes.count(), 1)
        self.assertTrue(Notificacion.objects.filter(usuario=self.vendedor, leida=False).exists())
        # Volver a abrir el chat no crea otra conversacion
        self.client.post(reverse('iniciar_chat', args=[self.producto.id]))
        self.assertEqual(Conversacion.objects.count(), 1)

    def test_vendedor_responde_y_recibe_solo_nuevos(self):
        chat = self.abrir_chat()
        primero = chat.mensajes.first()
        self.client.login(username='vendedor', password='clave12345')
        respuesta = self.client.post(reverse('enviar_mensaje', args=[chat.id]),
                                     {'texto': 'Sí, hay stock', 'despues': primero.id}, HTTP_HX_REQUEST='true')
        self.assertContains(respuesta, 'Sí, hay stock')
        self.assertNotContains(respuesta, 'Hola, ¿hay 100 kg?')
        primero.refresh_from_db()
        self.assertTrue(primero.leido)

    def test_otro_usuario_no_puede_leer_ni_escribir(self):
        chat = self.abrir_chat()
        self.client.login(username='intruso', password='clave12345')
        self.assertEqual(self.client.get(reverse('conversacion', args=[chat.id])).status_code, 403)
        self.assertEqual(self.client.get(reverse('mensajes_nuevos', args=[chat.id])).status_code, 403)
        self.assertEqual(self.client.post(reverse('enviar_mensaje', args=[chat.id]), {'texto': 'hola'}).status_code, 403)
        self.assertEqual(Mensaje.objects.count(), 1)

    def test_solicitud_desde_chat_y_cancelar(self):
        chat = self.abrir_chat()
        self.client.post(reverse('solicitud_desde_chat', args=[chat.id]),
                         {'cantidad': 100, 'precio_unitario_ofrecido': '2.80', 'mensaje': ''})
        solicitud = OfertaNegociacion.objects.get(producto=self.producto, comprador=self.comprador)
        self.assertEqual(solicitud.estado, 'PENDIENTE')
        self.assertIn('solicitud de compra', chat.mensajes.last().texto)
        self.client.post(reverse('responder_oferta', args=[solicitud.id]), {'decision': 'CANCELAR'})
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'CANCELADA')

    def test_favorito_se_agrega_y_quita(self):
        self.client.login(username='comprador', password='clave12345')
        url = reverse('alternar_favorito', args=[self.producto.id])
        datos = self.client.post(url, HTTP_X_RAPIDO='1').json()
        self.assertTrue(datos['favorito'])
        self.assertContains(self.client.get(reverse('mis_favoritos')), 'Papa')
        datos = self.client.post(url, HTTP_X_RAPIDO='1').json()
        self.assertFalse(datos['favorito'])
        self.assertFalse(Favorito.objects.exists())

    def test_perfil_publico_del_productor(self):
        respuesta = self.client.get(reverse('perfil_productor', args=[self.vendedor.id]))
        self.assertContains(respuesta, 'Papa')
        self.assertEqual(self.client.get(reverse('perfil_productor', args=[self.intruso.id])).status_code, 404)

    def test_aviso_de_publicacion_por_vencer_una_sola_vez(self):
        self.producto.fecha_vencimiento = timezone.now() + timedelta(days=1)
        self.producto.save()
        self.client.login(username='vendedor', password='clave12345')
        self.client.get(reverse('catalogo'))
        self.client.get(reverse('catalogo'))
        self.assertEqual(Notificacion.objects.filter(usuario=self.vendedor, icono='bi-hourglass-split').count(), 1)


class PruebasFotosExtra(TestCase):
    def setUp(self):
        self.carpeta = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.carpeta, ignore_errors=True)
        self.vendedor = User.objects.create_user('vendedor', password='clave12345')
        PerfilUsuario.objects.create(usuario=self.vendedor, rol='PRODUCTOR')
        self.producto = Producto.objects.create(
            productor=self.vendedor, nombre='Palta', descripcion='Palta Hass',
            precio=Decimal('6.00'), stock=80, origen='Cayma, Arequipa',
        )

    def test_maximo_cuatro_fotos_extra(self):
        from .views import guardar_fotos_extra
        from django.test import RequestFactory
        from django.contrib.messages.storage.fallback import FallbackStorage
        fotos = [SimpleUploadedFile(f'f{i}.jpg', b'x' * 10, content_type='image/jpeg') for i in range(6)]
        fotos.append(SimpleUploadedFile('virus.exe', b'x', content_type='application/octet-stream'))
        request = RequestFactory().post('/', {'fotos_extra': fotos})
        request.session = {}
        request._messages = FallbackStorage(request)
        with override_settings(MEDIA_ROOT=self.carpeta):
            guardar_fotos_extra(request, self.producto)
        self.assertEqual(self.producto.fotos.count(), 4)


class PruebasSeguridad(TestCase):
    def test_google_no_guarda_credenciales_desde_la_web(self):
        from django.conf import settings
        antes = getattr(settings, 'GOOGLE_CLIENT_SECRET', '')
        self.client.post(reverse('login_google'), {
            'guardar_credenciales_google': '1', 'google_client_id': 'id-falso', 'google_client_secret': 'secreto-falso',
        })
        self.assertEqual(getattr(settings, 'GOOGLE_CLIENT_SECRET', ''), antes)

    def test_google_callback_rechaza_estado_desconocido(self):
        respuesta = self.client.get(reverse('login_google_callback'), {'code': 'abc', 'state': 'PRODUCTOR'})
        self.assertRedirects(respuesta, reverse('login'), fetch_redirect_response=False)

    def test_culqi_con_clave_no_aprueba_sin_tarjeta(self):
        from .views import procesar_cobro_culqi
        with override_settings(CULQI_SECRET_KEY='sk_test_x'):
            exito, codigo, _ = procesar_cobro_culqi(Decimal('10'), 'a@b.com', '')
        self.assertFalse(exito)
        self.assertIsNone(codigo)
