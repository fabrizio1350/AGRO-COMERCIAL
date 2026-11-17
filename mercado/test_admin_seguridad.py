import time

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase


class AdminEstiloYSeguridadTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('jefe', 'jefe@ejemplo.com', 'ClaveMuySegura123')
        self.url = '/' + settings.ADMIN_URL

    def test_los_estilos_del_admin_cargan(self):
        respuesta = self.client.get(settings.STATIC_URL + 'admin/css/base.css')
        self.assertEqual(respuesta.status_code, 200)
        respuesta = self.client.get(settings.STATIC_URL + 'css/admin.css')
        self.assertEqual(respuesta.status_code, 200)

    def test_login_del_admin_usa_el_estilo_de_mercofertas(self):
        respuesta = self.client.get(self.url + 'login/')
        self.assertContains(respuesta, 'css/admin.css')
        self.assertContains(respuesta, 'Panel de administración')
        self.assertEqual(respuesta.headers['Cache-Control'], 'no-store, private')
        self.assertIn('noindex', respuesta.headers['X-Robots-Tag'])

    def test_sesion_del_admin_se_cierra_por_inactividad(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        sesion = self.client.session
        sesion['admin_ultimo_movimiento'] = int(time.time()) - (settings.ADMIN_MINUTOS_INACTIVO * 60 + 5)
        sesion.save()
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn('login', respuesta.url)

    def test_usuario_normal_no_entra_al_admin(self):
        normal = User.objects.create_user('vecino', 'v@ejemplo.com', 'ClaveMuySegura123')
        self.client.force_login(normal)
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_la_web_publica_no_lleva_cabeceras_del_admin(self):
        respuesta = self.client.get('/')
        self.assertNotIn('X-Robots-Tag', respuesta.headers)
