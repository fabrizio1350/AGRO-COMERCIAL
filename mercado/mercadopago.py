"""
Cobro de la publicidad de ofertas con Mercado Pago (Checkout Pro: Yape, tarjeta, etc.).

Como funciona:
1. El vendedor elige normal o premium y toca "Pagar con Mercado Pago".
2. Creamos un PagoComision PENDIENTE y una "preferencia" en Mercado Pago con su codigo (external_reference).
3. El vendedor paga en la pagina de Mercado Pago.
4. Mercado Pago avisa a /pagos/mercadopago/aviso/ (webhook) y ademas el vendedor vuelve a /pagos/mercadopago/vuelta/.
5. En los dos casos NO confiamos en lo que llega: consultamos el pago a la API de Mercado Pago con nuestra llave.
   Si esta aprobado, en soles, por el monto correcto y con nuestro codigo, la oferta se publica sola.

Llaves en el .env de la VPS (nunca en el codigo):
    MERCADOPAGO_ACCESS_TOKEN=APP_USR-...      (o TEST-... para probar)
    MERCADOPAGO_WEBHOOK_SECRET=...            (clave secreta de la seccion Webhooks, opcional pero recomendada)
"""
import hashlib
import hmac
import json
import logging
import urllib.error
import urllib.request
from decimal import Decimal

from django.conf import settings

API = 'https://api.mercadopago.com'
registro = logging.getLogger('mercado.pagos')


class ErrorMercadoPago(Exception):
    pass


def activo():
    return bool(settings.MERCADOPAGO_ACCESS_TOKEN)


def _pedir(metodo, ruta, datos=None, clave_idempotencia=None):
    cuerpo = json.dumps(datos).encode() if datos is not None else None
    solicitud = urllib.request.Request(API + ruta, data=cuerpo, method=metodo)
    solicitud.add_header('Authorization', f'Bearer {settings.MERCADOPAGO_ACCESS_TOKEN}')
    solicitud.add_header('Content-Type', 'application/json')
    if clave_idempotencia:
        solicitud.add_header('X-Idempotency-Key', clave_idempotencia)
    try:
        with urllib.request.urlopen(solicitud, timeout=12) as respuesta:
            return json.loads(respuesta.read().decode() or '{}')
    except urllib.error.HTTPError as error:
        registro.error('Mercado Pago respondio %s en %s %s', error.code, metodo, ruta)
        raise ErrorMercadoPago(f'Mercado Pago respondió {error.code}') from error
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        registro.error('No se pudo hablar con Mercado Pago: %s', error)
        raise ErrorMercadoPago('No se pudo conectar con Mercado Pago') from error


def crear_preferencia(pago, url_vuelta, url_aviso):
    """Devuelve la URL de Mercado Pago a la que se manda al vendedor para pagar."""
    datos = {
        'items': [{
            'id': f'oferta-{pago.producto_id}',
            'title': f'Publicidad de oferta {pago.get_tipo_oferta_display().lower()}: {pago.producto.nombre}'[:250],
            'quantity': 1,
            'currency_id': 'PEN',
            'unit_price': float(pago.monto),
        }],
        'external_reference': pago.codigo_transaccion,
        'statement_descriptor': 'MERCOFERTAS',
        'back_urls': {'success': url_vuelta, 'pending': url_vuelta, 'failure': url_vuelta},
        'auto_return': 'approved',
        'notification_url': url_aviso,
        'metadata': {'pago_id': pago.pk},
    }
    if pago.productor.email:
        datos['payer'] = {'email': pago.productor.email}
    respuesta = _pedir('POST', '/checkout/preferences', datos, clave_idempotencia=f'{pago.codigo_transaccion}-{pago.pk}')
    url = respuesta.get('init_point')
    if not url:
        raise ErrorMercadoPago('Mercado Pago no devolvió el enlace de pago')
    return url


def consultar_pago(pago_mp_id):
    return _pedir('GET', f'/v1/payments/{int(pago_mp_id)}')


def firma_valida(request, dato_id):
    """Revisa la cabecera x-signature que manda Mercado Pago. Si no hay clave configurada, no se exige
    (igual estamos seguros porque siempre volvemos a consultar el pago a la API)."""
    secreto = settings.MERCADOPAGO_WEBHOOK_SECRET
    if not secreto:
        return True
    firma = request.headers.get('x-signature', '')
    partes = dict(p.split('=', 1) for p in firma.split(',') if '=' in p)
    ts, v1 = partes.get('ts', '').strip(), partes.get('v1', '').strip()
    if not ts or not v1:
        return False
    manifiesto = f"id:{str(dato_id).lower()};request-id:{request.headers.get('x-request-id', '')};ts:{ts};"
    esperado = hmac.new(secreto.encode(), manifiesto.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperado, v1)


def aplicar_pago(pago_mp_id):
    """Consulta el pago en Mercado Pago y, si corresponde, confirma el PagoComision. Devuelve el PagoComision o None."""
    from .models import PagoComision
    datos = consultar_pago(pago_mp_id)
    referencia = datos.get('external_reference') or ''
    pago = PagoComision.objects.filter(codigo_transaccion=referencia, metodo_pago='MERCADOPAGO').select_related('producto').first()
    if not pago:
        registro.warning('Pago de Mercado Pago %s sin pago nuestro (%s)', pago_mp_id, referencia)
        return None
    estado = datos.get('status')
    if estado != 'approved':
        registro.info('Pago de Mercado Pago %s para %s esta en estado %s', pago_mp_id, referencia, estado)
        return pago
    monto = Decimal(str(datos.get('transaction_amount') or 0))
    if datos.get('currency_id') != 'PEN' or monto < pago.monto:
        registro.warning('Pago %s no coincide: %s %s, esperabamos S/ %s', pago_mp_id, datos.get('currency_id'), monto, pago.monto)
        return pago
    if pago.estado == 'PENDIENTE':
        numero = str(datos.get('id'))[:20]
        if not PagoComision.objects.filter(numero_operacion=numero).exclude(pk=pago.pk).exists():
            PagoComision.objects.filter(pk=pago.pk, estado='PENDIENTE').update(numero_operacion=numero)
        if pago.confirmar(None):
            registro.info('Pago %s confirmado solo por Mercado Pago (%s)', referencia, pago_mp_id)
    pago.refresh_from_db()
    return pago
