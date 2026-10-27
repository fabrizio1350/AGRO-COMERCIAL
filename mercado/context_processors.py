from django.conf import settings
from datetime import timedelta
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from .models import Categoria, PerfilUsuario, ItemCarrito, OfertaNegociacion, Producto, Mensaje, Notificacion, Favorito


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
            'mensajes_sin_leer': 0,
            'notificaciones_sin_leer': 0,
            'favoritos_ids': set(),
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

    if perfil.rol == 'PRODUCTOR':
        avisar_vencimientos(request.user)

    mensajes_sin_leer = Mensaje.objects.filter(
        Q(conversacion__comprador=request.user) | Q(conversacion__vendedor=request.user),
        leido=False,
    ).exclude(autor=request.user).count()

    return {
        'rol_actual': perfil.rol,
        'mensajes_sin_leer': mensajes_sin_leer,
        'notificaciones_sin_leer': Notificacion.objects.filter(usuario=request.user, leida=False).count(),
        'favoritos_ids': set(Favorito.objects.filter(usuario=request.user).values_list('producto_id', flat=True)),
        'perfil_global': perfil,
        'total_items_carrito': total_carrito,
        'ofertas_pendientes_vendedor': ofertas_vendedor,
        'ofertas_listas_comprador': ofertas_comprador,
    }


def avisar_vencimientos(usuario):
    """Avisa una sola vez al productor cuando una publicacion vence en menos de 3 dias."""
    ahora = timezone.now()
    por_vencer = Producto.objects.publicados().filter(productor=usuario, fecha_vencimiento__lte=ahora + timedelta(days=3))
    for producto in por_vencer:
        enlace = f"{reverse('panel_productor')}#producto-{producto.id}"
        ya_avisado = Notificacion.objects.filter(
            usuario=usuario, enlace=enlace, fecha__gte=producto.fecha_vencimiento - timedelta(days=3)
        ).exists()
        if not ya_avisado:
            Notificacion.avisar(
                usuario,
                f"Tu publicación {producto.nombre} vence pronto ({timezone.localtime(producto.fecha_vencimiento):%d/%m %H:%M}). Renuévala para que siga visible.",
                enlace, 'bi-hourglass-split',
            )
