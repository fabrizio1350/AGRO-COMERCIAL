from django.conf import settings
from .models import Categoria, PerfilUsuario, ItemCarrito, OfertaNegociacion


def datos_del_sitio(request):
    """Datos que usa la cabecera en todas las paginas (menu de categorias y version de estaticos)."""
    return {
        'categorias_menu': Categoria.objects.order_by('nombre'),
        'version_estaticos': settings.VERSION_ESTATICOS,
        'correo_contacto': settings.CORREO_CONTACTO,
    }


def datos_globales_usuario(request):
    """Provee informacion de rol, carrito y alertas de ofertas en todas las plantillas."""
    if not request.user.is_authenticated:
        return {
            'rol_actual': None,
            'perfil_global': None,
            'total_items_carrito': 0,
            'ofertas_pendientes_vendedor': 0,
            'ofertas_listas_comprador': 0,
        }

    perfil, _ = PerfilUsuario.objects.get_or_create(usuario=request.user)
    total_carrito = sum(item.cantidad for item in ItemCarrito.objects.filter(comprador=request.user))
    ofertas_vendedor = OfertaNegociacion.objects.filter(
        producto__productor=request.user,
        estado='PENDIENTE'
    ).count()
    ofertas_comprador = OfertaNegociacion.objects.filter(
        comprador=request.user,
        estado='ACEPTADA'
    ).count()

    return {
        'rol_actual': perfil.rol,
        'perfil_global': perfil,
        'total_items_carrito': total_carrito,
        'ofertas_pendientes_vendedor': ofertas_vendedor,
        'ofertas_listas_comprador': ofertas_comprador,
    }
