import io
import json
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import PerfilUsuario
from .views import crear_enlace_google

JPG = b'\xff\xd8\xff\xe0' + b'\x00' * 20


class PruebasVincularGoogle(TestCase):
    def setUp(self):
        cache.clear()

    def callback(self, sub, correo):
        sesion = self.client.session
        sesion['estado_google'] = 'estado-prueba'
        sesion.save()
        respuestas = [
            io.BytesIO(b'{"access_token": "token-de-prueba"}'),
            io.BytesIO(json.dumps({'sub': sub, 'email': correo, 'email_verified': True}).encode()),
        ]
        with patch('mercado.views.urllib.request.urlopen', side_effect=respuestas):
            return self.client.get(reverse('login_google_callback'), {'state': 'estado-prueba', 'code': 'codigo'})

    def cuenta_antigua(self, correo='antigua@gmail.com', clave=None):
        usuario = User.objects.create_user('antigua', email=correo, password=clave)
        PerfilUsuario.objects.create(usuario=usuario, rol='COMPRADOR')
        return usuario

    def test_enlace_del_administrador_vincula_la_cuenta_antigua(self):
        usuario = self.cuenta_antigua()
        self.client.get(reverse('enlace_google', args=[crear_enlace_google(usuario)]))
        self.callback('sub-antigua', 'antigua@gmail.com')
        self.assertEqual(PerfilUsuario.objects.get(usuario=usuario).google_sub, 'sub-antigua')
        self.assertEqual(self.client.session['_auth_user_id'], str(usuario.pk))
        # La proxima vez entra directo con Google
        self.client.logout()
        self.callback('sub-antigua', 'antigua@gmail.com')
        self.assertEqual(self.client.session['_auth_user_id'], str(usuario.pk))

    def test_enlace_exige_el_mismo_correo_en_google(self):
        usuario = self.cuenta_antigua()
        self.client.get(reverse('enlace_google', args=[crear_enlace_google(usuario)]))
        self.callback('sub-intruso', 'otra@gmail.com')
        self.assertIsNone(PerfilUsuario.objects.get(usuario=usuario).google_sub)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_enlace_alterado_no_sirve(self):
        usuario = self.cuenta_antigua()
        codigo = crear_enlace_google(usuario)[:-2] + 'xx'
        self.assertRedirects(self.client.get(reverse('enlace_google', args=[codigo])), reverse('login'),
                             fetch_redirect_response=False)
        self.assertNotIn('vincular_google', self.client.session)

    def test_vincular_desde_mi_perfil(self):
        usuario = self.cuenta_antigua(clave='Clave-segura-2026')
        self.client.force_login(usuario)
        self.client.post(reverse('vincular_google'))
        self.callback('sub-perfil', 'cualquier-gmail@gmail.com')
        self.assertEqual(PerfilUsuario.objects.get(usuario=usuario).google_sub, 'sub-perfil')

    def test_google_de_otra_cuenta_no_se_puede_vincular(self):
        otro = User.objects.create_user('otro', email='otro@gmail.com')
        PerfilUsuario.objects.create(usuario=otro, rol='COMPRADOR', google_sub='sub-ocupado')
        usuario = self.cuenta_antigua(clave='Clave-segura-2026')
        self.client.force_login(usuario)
        self.client.post(reverse('vincular_google'))
        self.callback('sub-ocupado', 'otro@gmail.com')
        self.assertIsNone(PerfilUsuario.objects.get(usuario=usuario).google_sub)

    def test_comando_crea_el_enlace(self):
        self.cuenta_antigua()
        salida = StringIO()
        call_command('enlace_google', 'antigua@gmail.com', '--sitio', 'https://agro.example', stdout=salida)
        self.assertIn('https://agro.example/login/google/enlace/', salida.getvalue())


class PruebasCorreoUnico(TestCase):
    def test_registro_rechaza_correo_repetido(self):
        User.objects.create_user('primera', email='Repetido@Gmail.com')
        respuesta = self.client.post(reverse('registro'), {
            'username': 'segunda', 'first_name': 'Ana', 'last_name': 'Paz', 'email': 'repetido@gmail.com',
            'rol': 'COMPRADOR', 'password1': 'Mercado-San-Camilo-8', 'password2': 'Mercado-San-Camilo-8',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(User.objects.filter(username='segunda').exists())

    def test_perfil_no_acepta_correo_de_otra_cuenta(self):
        User.objects.create_user('duena', email='duena@gmail.com')
        usuario = User.objects.create_user('yo', email='yo@gmail.com')
        PerfilUsuario.objects.create(usuario=usuario, rol='COMPRADOR')
        self.client.force_login(usuario)
        respuesta = self.client.post(reverse('perfil'), {'first_name': 'Yo', 'last_name': 'Mismo', 'email': 'DUENA@gmail.com'})
        self.assertContains(respuesta, 'Ese correo ya lo usa otra cuenta')
        usuario.refresh_from_db()
        self.assertEqual(usuario.email, 'yo@gmail.com')


class PruebasLimiteLogin(TestCase):
    def setUp(self):
        cache.clear()
        usuario = User.objects.create_user('vendedora', password='Clave-correcta-2026')
        PerfilUsuario.objects.create(usuario=usuario, rol='PRODUCTOR')

    def test_bloquea_despues_de_cinco_claves_equivocadas(self):
        for _ in range(5):
            self.client.post(reverse('login'), {'username': 'vendedora', 'password': 'mala'})
        respuesta = self.client.post(reverse('login'), {'username': 'vendedora', 'password': 'Clave-correcta-2026'})
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(respuesta, 'demasiados intentos')
        cache.clear()
        self.client.post(reverse('login'), {'username': 'vendedora', 'password': 'Clave-correcta-2026'})
        self.assertIn('_auth_user_id', self.client.session)


class PruebasFotosYCabeceras(TestCase):
    def test_foto_disfrazada_se_guarda_con_nombre_seguro(self):
        from .presencial import validar_foto
        archivo = validar_foto(SimpleUploadedFile('ataque.html', JPG + b'<script>alert(1)</script>', content_type='text/html'))
        self.assertTrue(archivo.name.endswith('.jpg'))
        self.assertNotIn('ataque', archivo.name)

    def test_cabeceras_de_seguridad(self):
        respuesta = self.client.get(reverse('login'))
        self.assertIn("frame-ancestors 'none'", respuesta['Content-Security-Policy'])
        self.assertIn('camera=()', respuesta['Permissions-Policy'])

    @override_settings(DEBUG=False)
    def test_login_sigue_funcionando_con_cabeceras(self):
        self.assertEqual(self.client.get(reverse('login'), secure=True).status_code, 200)
