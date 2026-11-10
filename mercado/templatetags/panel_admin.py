"""Datos para la portada del panel de administracion: lo que esta esperando revision."""
from django import template

from mercado.models import PagoComision, VerificacionVendedor

register = template.Library()


@register.simple_tag
def pendientes_admin():
    try:
        verificaciones = VerificacionVendedor.objects.filter(usuario__perfil__estado_verificacion='PENDIENTE').count()
    except Exception:
        verificaciones = 0
    return {'pagos': PagoComision.objects.filter(estado='PENDIENTE').count(), 'verificaciones': verificaciones}
