from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from .forms import ProductoForm
from .models import Categoria, PerfilUsuario, Producto


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
