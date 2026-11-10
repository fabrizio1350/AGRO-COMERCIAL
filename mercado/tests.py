from datetime import timedelta
from decimal import Decimal
import io
import json
from unittest.mock import patch
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
import shutil
import tempfile
from django.urls import reverse
from django.utils import timezone
from .forms import ProductoForm
from .models import Puesto, Categoria, PerfilUsuario, Producto, Conversacion, Mensaje, Notificacion, Favorito, OfertaNegociacion, ItemCarrito, Pedido, LUGAR_POR_DEFECTO


def dar_puesto(usuario, nombre='Mercado de prueba'):
    """Los productos solo se muestran si el vendedor marco su puesto en el mapa."""
    return Puesto.objects.create(vendedor=usuario, nombre=nombre, numero='1', latitud=Decimal('-16.40'), longitud=Decimal('-71.53'))


class PruebasOfertasYVencimiento(TestCase):
    def setUp(self):
        self.vendedor = User.objects.create_user('vendedor', password='clave12345', first_name='Ana')
        PerfilUsuario.objects.create(usuario=self.vendedor, rol='PRODUCTOR', estado_verificacion='VERIFICADO')
        dar_puesto(self.vendedor)
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

    def test_login_vendedor_lleva_al_panel(self):
        respuesta = self.client.post(reverse('login'), {'username': 'vendedor', 'password': 'clave12345'})
        self.assertRedirects(respuesta, reverse('panel_productor'), fetch_redirect_response=False)

    def test_registro_lleva_a_ofertas(self):
        respuesta = self.client.post(reverse('registro'), {
            'username': 'nuevo', 'first_name': 'Luis', 'last_name': 'Quispe', 'email': 'luis@example.com',
            'rol': 'COMPRADOR', 'password1': 'ClaveSegura2026!', 'password2': 'ClaveSegura2026!',
        })
        self.assertRedirects(respuesta, reverse('ventas_por_oferta'), fetch_redirect_response=False)

    def test_paginas_con_carrusel_cargan(self):
        self.crear(en_oferta=True, precio_oferta=Decimal('8.00'), oferta_fin=timezone.now() + timedelta(days=2),
                   tipo_oferta='PREMIUM')
        self.client.login(username='vendedor', password='clave12345')
        for nombre in ('ventas_por_oferta', 'catalogo'):
            respuesta = self.client.get(reverse(nombre))
            self.assertContains(respuesta, 'Ofertas de hoy' if nombre == 'ventas_por_oferta' else 'Productos disponibles')
            self.assertContains(respuesta, 'data-stock-id')
        respuesta = self.client.get(reverse('catalogo'), {'precio_max': '9', 'ofertas': '1', 'ubicacion': 'Cayma, Arequipa'})
        self.assertContains(respuesta, 'Palta')

    def test_renovar_publicacion_vencida(self):
        prod = self.crear(fecha_vencimiento=timezone.now() - timedelta(days=1))
        self.client.login(username='vendedor', password='clave12345')
        self.client.post(reverse('renovar_producto', args=[prod.id]))
        prod.refresh_from_db()
        self.assertFalse(prod.esta_vencida())



class PruebasChatYFavoritos(TestCase):
    def setUp(self):
        self.vendedor = User.objects.create_user('vendedor', password='clave12345', first_name='Ana')
        PerfilUsuario.objects.create(usuario=self.vendedor, rol='PRODUCTOR', estado_verificacion='VERIFICADO')
        dar_puesto(self.vendedor)
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
        PerfilUsuario.objects.create(usuario=self.vendedor, rol='PRODUCTOR', estado_verificacion='VERIFICADO')
        dar_puesto(self.vendedor)
        self.producto = Producto.objects.create(
            productor=self.vendedor, nombre='Palta', descripcion='Palta Hass',
            precio=Decimal('6.00'), stock=80, origen='Cayma, Arequipa',
        )

    def test_maximo_cuatro_fotos_extra(self):
        from .views import guardar_fotos_extra
        from django.test import RequestFactory
        from django.contrib.messages.storage.fallback import FallbackStorage
        fotos = [SimpleUploadedFile(f'f{i}.jpg', b'\xff\xd8\xff' + b'x' * 10, content_type='image/jpeg') for i in range(6)]
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


class PruebasIdentidadGoogle(TestCase):
    def callback(self, sub, correo, verificado=True):
        sesion = self.client.session
        sesion['estado_google'] = 'estado-prueba'
        sesion.save()
        respuestas = [
            io.BytesIO(b'{"access_token": "token-de-prueba"}'),
            io.BytesIO(json.dumps({'sub': sub, 'email': correo, 'email_verified': verificado}).encode()),
        ]
        with patch('mercado.views.urllib.request.urlopen', side_effect=respuestas):
            return self.client.get(reverse('login_google_callback'), {'state': 'estado-prueba', 'code': 'codigo'})

    def test_coincidencia_de_correo_no_autentica_cuenta_local(self):
        User.objects.create_user('cuenta_local', email='colision@example.com')
        self.assertRedirects(self.callback('identidad-nueva', 'colision@example.com'), reverse('login'),
                             fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertFalse(PerfilUsuario.objects.filter(google_sub='identidad-nueva').exists())

    def test_correo_verificado_y_login_por_identificador_estable(self):
        self.callback('identidad-nueva', 'google@example.com', verificado=False)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.callback('identidad-nueva', 'google@example.com')
        perfil = PerfilUsuario.objects.get(google_sub='identidad-nueva')
        self.assertEqual(self.client.session['_auth_user_id'], str(perfil.usuario_id))
        self.client.logout()
        self.callback('identidad-nueva', 'otro-correo@example.com')
        self.assertEqual(self.client.session['_auth_user_id'], str(perfil.usuario_id))


class PruebasDatosDemo(TestCase):
    def test_comando_crea_bots_demo_sin_duplicar_y_los_borra(self):
        from django.core.management import call_command
        from io import StringIO
        call_command('crear_datos_demo', stdout=StringIO())
        call_command('crear_datos_demo', stdout=StringIO())
        bots = PerfilUsuario.objects.filter(es_demo=True, usuario__username__startswith='demo_')
        self.assertEqual(bots.count(), 17)
        self.assertEqual(Producto.objects.filter(productor__perfil__es_demo=True).count(), 19)
        from .models import Conversacion, VentaPuesto
        self.assertEqual(Conversacion.objects.filter(comprador__perfil__es_demo=True).count(), 4)
        self.assertTrue(VentaPuesto.objects.filter(vendedor__perfil__es_demo=True).exists())
        self.assertFalse(VentaPuesto.objects.filter(fecha__gt=timezone.now()).exists())
        self.assertFalse(any(p.usuario.has_usable_password() for p in bots))
        self.assertContains(self.client.get(reverse('catalogo')), 'Demo')
        call_command('crear_datos_demo', '--borrar', stdout=StringIO())
        self.assertFalse(PerfilUsuario.objects.filter(usuario__username__startswith='demo_').exists())


class PruebasCuentaHibrida(TestCase):
    def setUp(self):
        self.vendedor = User.objects.create_user('vendedor', password='clave12345')
        PerfilUsuario.objects.create(usuario=self.vendedor, rol='PRODUCTOR', estado_verificacion='VERIFICADO')
        dar_puesto(self.vendedor)
        self.otro = User.objects.create_user('otro_vendedor', password='clave12345')
        PerfilUsuario.objects.create(usuario=self.otro, rol='PRODUCTOR', estado_verificacion='VERIFICADO')
        dar_puesto(self.otro)
        self.producto = Producto.objects.create(
            productor=self.otro, nombre='Ajo', descripcion='Ajo morado',
            precio=Decimal('8.00'), stock=100, origen='Yarabamba, Arequipa',
        )

    def test_ya_no_existe_el_cambio_de_modo(self):
        self.client.login(username='vendedor', password='clave12345')
        self.assertEqual(self.client.post('/cambiar-modo/', {'nuevo_rol': 'COMPRADOR'}).status_code, 404)
        self.assertEqual(PerfilUsuario.objects.get(usuario=self.vendedor).rol, 'PRODUCTOR')

    def test_vendedor_tambien_compra_chatea_y_guarda_favoritos(self):
        self.client.login(username='vendedor', password='clave12345')
        self.client.post(reverse('iniciar_chat', args=[self.producto.id]), {'texto': 'hola'})
        self.client.post(reverse('alternar_favorito', args=[self.producto.id]))
        self.client.post(reverse('agregar_al_carrito', args=[self.producto.id]), {'cantidad': 2})
        self.assertTrue(Conversacion.objects.filter(comprador=self.vendedor, vendedor=self.otro).exists())
        self.assertTrue(Favorito.objects.filter(usuario=self.vendedor).exists())
        self.assertTrue(ItemCarrito.objects.filter(comprador=self.vendedor, producto=self.producto, cantidad=2).exists())
        self.assertContains(self.client.get(reverse('carrito')), 'Ajo')
        self.assertEqual(self.client.get(reverse('panel_productor')).status_code, 200)

    def test_vendedor_no_compra_su_propio_producto(self):
        self.client.login(username='otro_vendedor', password='clave12345')
        self.client.post(reverse('agregar_al_carrito', args=[self.producto.id]), {'cantidad': 1})
        self.client.post(reverse('alternar_favorito', args=[self.producto.id]))
        self.assertFalse(ItemCarrito.objects.exists())
        self.assertFalse(Favorito.objects.exists())
        self.assertContains(self.client.get(reverse('detalle_producto', args=[self.producto.id])), 'Editar producto')


JPG_MINIMO = b'\xff\xd8\xff\xe0' + b'0' * 64


class PruebasVerificacionVendedor(TestCase):
    def setUp(self):
        from .models import almacen_privado
        self.almacen = almacen_privado
        self.carpeta = tempfile.mkdtemp()
        self.ubicacion_original = almacen_privado._location
        self._usar_carpeta(self.carpeta)
        self.vendedor = User.objects.create_user('nuevo_vendedor', password='clave12345', first_name='Rosa')
        self.perfil = PerfilUsuario.objects.create(usuario=self.vendedor, rol='PRODUCTOR')
        self.producto = Producto.objects.create(
            productor=self.vendedor, nombre='Cebolla', descripcion='Cebolla roja',
            precio=Decimal('2.00'), stock=500, origen='Majes, Arequipa',
        )
        self.admin = User.objects.create_superuser('jefe', 'jefe@example.com', 'clave12345')

    def tearDown(self):
        self._usar_carpeta(self.ubicacion_original)
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def _usar_carpeta(self, ruta):
        self.almacen._location = ruta
        for propiedad in ('base_location', 'location'):
            self.almacen.__dict__.pop(propiedad, None)

    def _datos(self, **cambios):
        datos = {
            'dni': '45678912', 'celular': '987654321', 'declara_puesto': 'on', 'acepta_tratamiento_datos': 'on',
            'foto_documento': SimpleUploadedFile('dni.jpg', JPG_MINIMO, content_type='image/jpeg'),
            'foto_en_puesto': SimpleUploadedFile('puesto.jpg', JPG_MINIMO, content_type='image/jpeg'),
        }
        datos.update(cambios)
        return datos

    def test_ruc_valido(self):
        from .models import ruc_valido
        self.assertTrue(ruc_valido('20601106699'))
        self.assertFalse(ruc_valido('20601106690'))
        self.assertFalse(ruc_valido('12345678901'))

    def test_producto_sin_puesto_esta_oculto(self):
        self.assertNotIn(self.producto, Producto.objects.publicados())
        self.assertEqual(self.client.get(reverse('detalle_producto', args=[self.producto.id])).status_code, 404)
        # El propio vendedor si puede verlo
        self.client.login(username='nuevo_vendedor', password='clave12345')
        self.assertContains(self.client.get(reverse('detalle_producto', args=[self.producto.id])), 'Solo tú ves este producto')

    def test_sin_verificar_se_muestra_salvo_que_sea_obligatorio(self):
        dar_puesto(self.vendedor)
        self.assertIn(self.producto, Producto.objects.publicados())
        self.assertNotContains(self.client.get(reverse('detalle_producto', args=[self.producto.id])), 'Puesto verificado')
        with self.settings(VERIFICACION_OBLIGATORIA=True):
            self.assertNotIn(self.producto, Producto.objects.publicados())
            self.assertEqual(self.client.get(reverse('detalle_producto', args=[self.producto.id])).status_code, 404)

    def test_verificar_pide_marcar_el_puesto_primero(self):
        self.client.login(username='nuevo_vendedor', password='clave12345')
        self.assertRedirects(self.client.get(reverse('verificacion_vendedor')), reverse('configurar_puesto'))

    def test_registro_de_vendedor_lleva_a_verificacion(self):
        respuesta = self.client.post(reverse('registro'), {
            'username': 'otro_productor', 'first_name': 'Luis', 'last_name': 'Mamani', 'email': 'luis@example.com',
            'rol': 'PRODUCTOR', 'password1': 'ClaveSegura123', 'password2': 'ClaveSegura123',
            'ubicacion': 'Cayma, Arequipa',
        })
        self.assertRedirects(respuesta, reverse('configurar_puesto'))

    def test_envio_queda_pendiente_y_avisa_al_admin(self):
        from .models import VerificacionVendedor
        dar_puesto(self.vendedor, 'Mercado San Camilo')
        self.client.login(username='nuevo_vendedor', password='clave12345')
        respuesta = self.client.post(reverse('verificacion_vendedor'), self._datos())
        self.assertRedirects(respuesta, reverse('verificacion_vendedor'))
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.estado_verificacion, 'PENDIENTE')
        self.assertTrue(Notificacion.objects.filter(usuario=self.admin).exists())
        self.assertIn('Mercado San Camilo', VerificacionVendedor.objects.get(usuario=self.vendedor).distrito)
        # Mientras se revisa, el producto se sigue viendo
        self.assertIn(self.producto, Producto.objects.publicados())

    def test_reglas_del_formulario(self):
        dar_puesto(self.vendedor)
        self.client.login(username='nuevo_vendedor', password='clave12345')
        sin_declarar = self._datos()
        sin_declarar.pop('declara_puesto')
        self.assertContains(self.client.post(reverse('verificacion_vendedor'), sin_declarar), 'confirmar que atiendes ese puesto')
        falso = self._datos(foto_en_puesto=SimpleUploadedFile('puesto.jpg', b'no soy una foto', content_type='image/jpeg'))
        self.assertContains(self.client.post(reverse('verificacion_vendedor'), falso), 'No pudimos abrir ese archivo')
        con_ruc = self._datos(ruc='20601106690')
        self.assertContains(self.client.post(reverse('verificacion_vendedor'), con_ruc), 'Ese RUC no es válido')
        self.assertContains(self.client.post(reverse('verificacion_vendedor'), self._datos(dni='123')), 'El DNI tiene 8 dígitos')
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.estado_verificacion, 'SIN_ENVIAR')

    def test_admin_aprueba_y_el_producto_se_publica(self):
        from .models import VerificacionVendedor
        dar_puesto(self.vendedor)
        self.client.login(username='nuevo_vendedor', password='clave12345')
        self.client.post(reverse('verificacion_vendedor'), self._datos())
        verificacion = VerificacionVendedor.objects.get(usuario=self.vendedor)
        self.client.login(username='jefe', password='clave12345')
        url = reverse('admin:mercado_verificacionvendedor_changelist')
        # Sin marcar lo comprobado no se aprueba
        self.client.post(url, {'action': 'aprobar', '_selected_action': [verificacion.id]})
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.estado_verificacion, 'PENDIENTE')
        VerificacionVendedor.objects.filter(id=verificacion.id).update(revisado_identidad=True, revisado_puesto=True)
        self.client.post(url, {'action': 'aprobar', '_selected_action': [verificacion.id]})
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.estado_verificacion, 'VERIFICADO')
        self.assertFalse(self.perfil.organico_verificado)
        self.assertIn(self.producto, Producto.objects.publicados())
        self.assertTrue(Notificacion.objects.filter(usuario=self.vendedor, texto__icontains='verificado').exists())
        self.client.logout()
        self.assertContains(self.client.get(reverse('detalle_producto', args=[self.producto.id])), 'Puesto verificado')
        self.assertContains(self.client.get(reverse('perfil_productor', args=[self.vendedor.id])), 'Verificado')

    def test_documentos_solo_los_ve_el_personal(self):
        from .models import VerificacionVendedor
        dar_puesto(self.vendedor)
        self.client.login(username='nuevo_vendedor', password='clave12345')
        self.client.post(reverse('verificacion_vendedor'), self._datos())
        verificacion = VerificacionVendedor.objects.get(usuario=self.vendedor)
        url = reverse('archivo_verificacion', args=[verificacion.id, 'foto_documento'])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.logout()
        self.assertNotEqual(self.client.get(url).status_code, 200)
        self.client.login(username='jefe', password='clave12345')
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta['Content-Disposition'].startswith('attachment;'))
        self.assertEqual(b''.join(respuesta.streaming_content), JPG_MINIMO)
        personal = User.objects.create_user('personal_sin_permiso', is_staff=True)
        self.client.force_login(personal)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(reverse('archivo_verificacion', args=[verificacion.id, 'usuario'])).status_code, 404)
        # El archivo no queda dentro de la carpeta publica media
        self.assertTrue(verificacion.foto_documento.path.startswith(self.carpeta))
