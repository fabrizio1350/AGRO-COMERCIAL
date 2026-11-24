import hashlib
import hmac
import json
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from . import mercadopago
from .models import Categoria, PagoComision, PerfilUsuario, Producto, Puesto


@override_settings(MERCADOPAGO_ACCESS_TOKEN='TEST-123', MERCADOPAGO_WEBHOOK_SECRET='')
class MercadoPagoTests(TestCase):
    def setUp(self):
        self.vendedor = User.objects.create_user('mp_vendedor', email='v@ejemplo.com')
        PerfilUsuario.objects.create(usuario=self.vendedor, rol='PRODUCTOR', ofertas_premium_regalo=0, ofertas_normal_regalo=0)
        Puesto.objects.create(vendedor=self.vendedor, nombre='Mercado', latitud=Decimal('-16.4'), longitud=Decimal('-71.5'))
        self.producto = Producto.objects.create(
            productor=self.vendedor, nombre='Palta', descripcion='x', precio=Decimal('8'), precio_oferta=Decimal('6'),
            en_oferta=True, oferta_pendiente_pago=True, stock=5, categoria=Categoria.objects.create(nombre='Frutas'))
        self.client.force_login(self.vendedor)

    def iniciar(self, tipo='PREMIUM'):
        with mock.patch.object(mercadopago, '_pedir', return_value={'init_point': 'https://www.mercadopago.com.pe/checkout/x'}) as pedir:
            respuesta = self.client.post(reverse('pagar_con_mercadopago', args=[self.producto.pk]), {'tipo_oferta': tipo})
        return respuesta, pedir

    def pago_mp(self, **cambios):
        pago = PagoComision.objects.get(estado='PENDIENTE')
        datos = {'id': 987654321, 'status': 'approved', 'currency_id': 'PEN', 'transaction_amount': float(pago.monto),
                 'external_reference': pago.codigo_transaccion}
        datos.update(cambios)
        return datos

    def test_boton_aparece_y_manda_a_mercado_pago_con_el_monto_del_servidor(self):
        self.assertContains(self.client.get(reverse('pagar_comision_oferta', args=[self.producto.pk])), 'con Yape o tarjeta')
        respuesta, pedir = self.iniciar('NORMAL')
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta['Location'].startswith('https://www.mercadopago.com.pe/'))
        enviado = pedir.call_args.args[2]
        self.assertEqual(enviado['items'][0]['unit_price'], float(Producto.tarifa_oferta('NORMAL')))
        self.assertEqual(enviado['items'][0]['currency_id'], 'PEN')
        pago = PagoComision.objects.get()
        self.assertEqual((pago.metodo_pago, pago.estado, enviado['external_reference']), ('MERCADOPAGO', 'PENDIENTE', pago.codigo_transaccion))

    def test_aviso_aprobado_publica_la_oferta_sola(self):
        self.iniciar()
        with mock.patch.object(mercadopago, '_pedir', return_value=self.pago_mp()):
            r = self.client.post(reverse('mercadopago_aviso') + '?type=payment&data.id=987654321',
                                 data=json.dumps({'type': 'payment', 'data': {'id': '987654321'}}), content_type='application/json')
        self.assertEqual(r.status_code, 200)
        pago = PagoComision.objects.get()
        self.assertEqual((pago.estado, pago.numero_operacion), ('CONFIRMADO', '987654321'))
        self.producto.refresh_from_db()
        self.assertFalse(self.producto.oferta_pendiente_pago)
        self.assertEqual(self.producto.tipo_oferta, 'PREMIUM')

    def test_no_publica_si_no_esta_aprobado_o_el_monto_no_cuadra(self):
        self.iniciar()
        for cambios in ({'status': 'rejected'}, {'transaction_amount': 0.1}, {'currency_id': 'USD'}, {'external_reference': 'OTRO'}):
            with mock.patch.object(mercadopago, '_pedir', return_value=self.pago_mp(**cambios)):
                self.client.post(reverse('mercadopago_aviso') + '?type=payment&data.id=987654321')
        self.assertEqual(PagoComision.objects.get().estado, 'PENDIENTE')
        self.producto.refresh_from_db()
        self.assertTrue(self.producto.oferta_pendiente_pago)

    def test_vuelta_consulta_la_api_y_no_confia_en_los_parametros(self):
        self.iniciar()
        with mock.patch.object(mercadopago, '_pedir', return_value=self.pago_mp(status='rejected')):
            self.client.get(reverse('mercadopago_vuelta'), {'payment_id': '987654321', 'status': 'approved'})
        self.assertEqual(PagoComision.objects.get().estado, 'PENDIENTE')
        with mock.patch.object(mercadopago, '_pedir', return_value=self.pago_mp()):
            r = self.client.get(reverse('mercadopago_vuelta'), {'payment_id': '987654321', 'status': 'approved'})
        self.assertRedirects(r, reverse('panel_productor'), fetch_redirect_response=False)
        self.assertEqual(PagoComision.objects.get().estado, 'CONFIRMADO')

    def test_volver_a_intentar_cierra_el_intento_anterior(self):
        self.iniciar()
        self.iniciar()
        self.assertEqual(PagoComision.objects.filter(estado='PENDIENTE').count(), 1)
        self.assertEqual(PagoComision.objects.filter(estado='RECHAZADO').count(), 1)

    @override_settings(MERCADOPAGO_WEBHOOK_SECRET='secreto')
    def test_firma_del_aviso(self):
        self.iniciar()
        url = reverse('mercadopago_aviso') + '?type=payment&data.id=987654321'
        self.assertFalse(mercadopago.firma_valida(mock.Mock(headers={'x-signature': 'ts=1,v1=malo', 'x-request-id': 'r1'}), '987654321'))
        # Un aviso falso no publica nada: la API dice que el pago no esta aprobado
        with mock.patch.object(mercadopago, '_pedir', return_value=self.pago_mp(status='pending')):
            self.client.post(url, HTTP_X_SIGNATURE='ts=1,v1=malo', HTTP_X_REQUEST_ID='r1')
        self.assertEqual(PagoComision.objects.get().estado, 'PENDIENTE')
        firma = hmac.new(b'secreto', b'id:987654321;request-id:r1;ts:1;', hashlib.sha256).hexdigest()
        with mock.patch.object(mercadopago, '_pedir', return_value=self.pago_mp()):
            r = self.client.post(url, HTTP_X_SIGNATURE=f'ts=1,v1={firma}', HTTP_X_REQUEST_ID='r1')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(PagoComision.objects.get().estado, 'CONFIRMADO')

    @override_settings(MERCADOPAGO_ACCESS_TOKEN='')
    def test_sin_llave_no_aparece_el_boton(self):
        self.assertNotContains(self.client.get(reverse('pagar_comision_oferta', args=[self.producto.pk])), 'con Yape o tarjeta')
        self.assertEqual(self.client.post(reverse('pagar_con_mercadopago', args=[self.producto.pk])).status_code, 404)
