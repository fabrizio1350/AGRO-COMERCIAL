"""Vistas del mercado presencial: el vendedor publica lo que tiene en su puesto y el comprador
arma su lista, ve el stock en tiempo real y va al puesto a comprar (no hay pago en linea)."""
from decimal import Decimal

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Avg, Count, F, Q, Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

import uuid

from .models import (
    Categoria, CuentaSinPagoOferta, ItemCarrito, Notificacion, PagoComision, Producto, Puesto, ResenaProducto, VentaPuesto,
    fecha_vencimiento_por_defecto,
)
from .forms import ResenaForm
from .seguridad import renombrar_imagen, tipo_de_imagen
from .views import asegurar_datos_iniciales, obtener_o_crear_perfil, ofertas_destacadas, con_precio_vigente

UNIDADES_MERCADO = ['UNIDAD', 'KG', 'DOCENA', 'ATADO', 'BOLSA', 'CAJA', 'SACO']


def validar_foto(archivo):
    if not archivo or not hasattr(archivo, 'content_type'):
        return archivo
    if archivo.size > 5 * 1024 * 1024:
        raise forms.ValidationError('La foto debe pesar como máximo 5 MB.')
    extension = tipo_de_imagen(archivo)
    if not extension:
        raise forms.ValidationError('Selecciona una foto JPG, PNG o WEBP.')
    return renombrar_imagen(archivo, extension)


class PuestoForm(forms.ModelForm):
    class Meta:
        model = Puesto
        fields = ('nombre', 'numero', 'referencia', 'direccion', 'horario', 'foto', 'latitud', 'longitud',
                  'efectivo', 'tarjeta', 'yape_plin')
        labels = {'nombre': 'Nombre del lugar', 'numero': 'N.º de puesto', 'foto': 'Foto de tu puesto'}
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Mercado San Camilo'}),
            'numero': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. 24'}),
            'referencia': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. pasillo de frutas, frente a la puerta 2'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Se llena sola al marcar el mapa'}),
            'horario': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Lunes a sábado, 6 a. m. a 2 p. m.'}),
            'foto': forms.FileInput(attrs={'class': 'd-none', 'accept': 'image/jpeg,image/png,image/webp'}),
            'latitud': forms.HiddenInput(),
            'longitud': forms.HiddenInput(),
            'efectivo': forms.CheckboxInput(attrs={'class': 'btn-check'}),
            'tarjeta': forms.CheckboxInput(attrs={'class': 'btn-check'}),
            'yape_plin': forms.CheckboxInput(attrs={'class': 'btn-check'}),
        }
        error_messages = {
            'latitud': {'required': 'Marca en el mapa dónde está tu puesto.'},
            'longitud': {'required': 'Marca en el mapa dónde está tu puesto.'},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['foto'].required = not (self.instance and self.instance.foto)
        # No todos los puestos tienen numero o un mercado con nombre: nada de esto es obligatorio
        self.fields['nombre'].required = False

    def clean_foto(self):
        return validar_foto(self.cleaned_data['foto'])

    def clean(self):
        datos = super().clean()
        if not (datos.get('nombre') or '').strip():
            vendedor = self.instance.vendedor if self.instance.vendedor_id else None
            nombre = (vendedor.first_name or vendedor.username) if vendedor else ''
            datos['nombre'] = f'Puesto de {nombre}'[:100] if nombre else 'Mi puesto'
        if not any(datos.get(campo) for campo in ('efectivo', 'tarjeta', 'yape_plin')):
            raise forms.ValidationError('Elige al menos una forma de pago.')
        return datos


class PublicacionForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ('nombre', 'categoria', 'descripcion', 'imagen', 'unidad', 'stock', 'precio',
                  'precio_oferta', 'disponible')
        labels = {'nombre': '¿Qué vendes?', 'imagen': 'Foto del producto', 'precio': 'Precio normal (S/)',
                  'precio_oferta': 'Precio de oferta (S/)', 'disponible': 'Mostrar en la web',
                  'stock': 'Cantidad que tienes', 'unidad': 'Se vende por', 'descripcion': 'Descripción corta'}
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Palta fuerte'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Ej. Palta madura para hoy, de Majes.'}),
            'imagen': forms.FileInput(attrs={'accept': 'image/jpeg,image/png,image/webp', 'class': 'd-none'}),
            'unidad': forms.Select(attrs={'class': 'form-select'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'inputmode': 'numeric'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.10', 'min': '0.10', 'inputmode': 'decimal'}),
            'precio_oferta': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.10', 'min': '0.10', 'inputmode': 'decimal', 'placeholder': 'Opcional'}),
            'disponible': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].empty_label = 'Elige una categoría'
        self.fields['categoria'].queryset = Categoria.objects.order_by('nombre')
        self.fields['descripcion'].required = False
        actual = self.instance.unidad if self.instance and self.instance.pk else None
        self.fields['unidad'].choices = [c for c in Producto.UNIDADES if c[0] in UNIDADES_MERCADO or c[0] == actual]
        if not self.instance.pk:
            self.initial.setdefault('unidad', 'KG')
            self.initial.setdefault('disponible', True)

    def clean_imagen(self):
        return validar_foto(self.cleaned_data['imagen'])

    def clean(self):
        datos = super().clean()
        precio = datos.get('precio')
        oferta = datos.get('precio_oferta')
        if precio is not None and precio <= 0:
            self.add_error('precio', 'Ingresa un precio mayor a cero.')
        if oferta is not None and (precio is None or not 0 < oferta < precio):
            self.add_error('precio_oferta', 'El precio de oferta debe ser menor al precio normal.')
        return datos


def es_vendedor(usuario):
    return obtener_o_crear_perfil(usuario).rol == 'PRODUCTOR'


def puestos_con_productos():
    publicados = Producto.objects.publicados()
    return (Puesto.objects.select_related('vendedor__perfil')
            .annotate(total_productos=Count('vendedor__productos', filter=Q(vendedor__productos__in=publicados)))
            .filter(total_productos__gt=0)
            .order_by('-total_productos', 'nombre'))


def datos_stock(producto):
    return {
        'stock': producto.stock,
        'unidad': producto.nombre_unidad_stock(),
        'precio': str(producto.precio_actual()),
        'disponible': producto.esta_publicado(),
        'actualizado': timezone.localtime(producto.stock_actualizado).strftime('%H:%M') if producto.stock_actualizado else '',
    }


# ---------------------------------------------------------------- comprador

def inicio(request):
    asegurar_datos_iniciales()
    publicados = Producto.objects.publicados().select_related('categoria', 'productor__puesto', 'productor__perfil')
    ofertas = ofertas_destacadas()
    puestos = puestos_con_productos()
    return render(request, 'inicio.html', {
        'categorias': Categoria.objects.annotate(total=Count('productos', filter=Q(productos__in=Producto.objects.publicados())))
                      .filter(total__gt=0).order_by('-total', 'nombre')[:8],
        'productos_destacados': publicados.order_by('-en_oferta', '-fecha_publicacion')[:8],
        'ofertas_carrusel': ofertas,
        'mejor_oferta': ofertas[0] if ofertas else None,
        'puestos_destacados': puestos[:6],
        'total_productos': publicados.count(),
        'total_ofertas': Producto.objects.ofertas_activas().count(),
        'total_puestos': puestos.count(),
    })


def catalogo(request, ofertas=False):
    asegurar_datos_iniciales()
    base = Producto.objects.ofertas_activas() if ofertas else Producto.objects.publicados()
    productos = con_precio_vigente(base.select_related('categoria', 'productor__puesto', 'productor__perfil'))
    busqueda = request.GET.get('q', '').strip()[:100]
    categoria_id = request.GET.get('categoria', '').strip()
    puesto_id = request.GET.get('puesto', '').strip()
    orden = request.GET.get('orden', 'recientes')
    if busqueda:
        productos = productos.filter(
            Q(nombre__icontains=busqueda) | Q(descripcion__icontains=busqueda)
            | Q(productor__puesto__nombre__icontains=busqueda) | Q(categoria__nombre__icontains=busqueda)
        )
    if categoria_id.isdigit():
        productos = productos.filter(categoria_id=int(categoria_id))
    if puesto_id.isdigit():
        productos = productos.filter(productor__puesto__id=int(puesto_id))
    if orden == 'precio_asc':
        productos = productos.order_by('precio_vigente')
    elif orden == 'precio_desc':
        productos = productos.order_by('-precio_vigente')
    elif orden == 'stock':
        productos = productos.order_by('-stock')
    else:
        orden = 'recientes'
        productos = productos.order_by('-en_oferta', '-fecha_publicacion')

    pagina = Paginator(productos, 12).get_page(request.GET.get('pagina'))
    parametros = request.GET.copy()
    parametros.pop('pagina', None)
    contexto = {
        'productos': pagina, 'pagina': pagina, 'parametros_filtro': parametros.urlencode(),
        'total_resultados': pagina.paginator.count, 'ofertas': ofertas,
        'ofertas_carrusel': ofertas_destacadas() if ofertas else None,
        'categorias': Categoria.objects.filter(productos__in=Producto.objects.publicados()).distinct().order_by('nombre'),
        'puestos': puestos_con_productos(),
        'busqueda': busqueda, 'categoria_seleccionada': categoria_id, 'puesto_seleccionado': puesto_id,
        'orden_seleccionado': orden,
    }
    return render(request, 'catalogo.html', contexto)


def ficha(request, producto_id):
    producto = get_object_or_404(
        Producto.objects.select_related('productor__puesto', 'productor__perfil', 'categoria'), pk=producto_id)
    if request.user != producto.productor and not producto.vendedor_habilitado():
        raise Http404()
    en_lista = None
    if request.user.is_authenticated:
        en_lista = ItemCarrito.objects.filter(comprador=request.user, producto=producto,
                                              precio_unitario_acordado__isnull=True).first()
    mas_del_puesto = (Producto.objects.publicados().filter(productor=producto.productor)
                      .exclude(pk=producto.pk).select_related('categoria', 'productor__puesto', 'productor__perfil')[:4])
    resenas = ResenaProducto.objects.filter(producto=producto).select_related('autor__perfil')
    mi_resena = resenas.filter(autor=request.user).first() if request.user.is_authenticated else None
    promedio = resenas.aggregate(p=Avg('calificacion'))['p']
    return render(request, 'detalle_producto.html', {
        'producto': producto, 'puesto': getattr(producto.productor, 'puesto', None),
        'en_lista': en_lista, 'mas_del_puesto': mas_del_puesto,
        'extras': producto.fotos.all(),
        'resenas': resenas[:20],
        'total_resenas': resenas.count(),
        'promedio_resenas': promedio,
        'estrellas_promedio': round(promedio or 0),
        'mi_resena': mi_resena,
        'resena_form': ResenaForm(instance=mi_resena),
    })


@login_required
@require_POST
def opinar(request, producto_id):
    """Guarda la calificacion de un producto. Cada persona tiene una sola opinion por producto y la puede cambiar."""
    producto = get_object_or_404(Producto, pk=producto_id)
    destino = f"{reverse('detalle_producto', args=[producto.pk])}#opiniones"
    if producto.productor_id == request.user.id:
        messages.info(request, 'No puedes calificar tus propios productos.')
        return redirect(destino)
    anterior = ResenaProducto.objects.filter(producto=producto, autor=request.user).first()
    form = ResenaForm(request.POST, instance=anterior)
    if not form.is_valid() or not 1 <= form.cleaned_data['calificacion'] <= 5:
        messages.warning(request, 'Elige de 1 a 5 estrellas y escribe un comentario corto.')
        return redirect(destino)
    resena = form.save(commit=False)
    resena.producto = producto
    resena.autor = request.user
    resena.comentario = resena.comentario.strip()[:1000]
    resena.save()
    if anterior is None:
        Notificacion.avisar(producto.productor,
                            f'{request.user.first_name or request.user.username} calificó {producto.nombre} con {resena.calificacion} estrella{"s" if resena.calificacion != 1 else ""}.',
                            destino, 'bi-star')
    messages.success(request, '¡Gracias! Tu opinión ya se ve en el producto.' if anterior is None else 'Actualizaste tu opinión.')
    return redirect(destino)


def puestos(request):
    lista_puestos = list(puestos_con_productos())
    puntos = [{
        'nombre': p.nombre, 'puesto': p.titulo_puesto(), 'productos': p.total_productos,
        'lat': float(p.latitud), 'lng': float(p.longitud), 'llegar': p.como_llegar(),
        'url': f"{reverse('catalogo')}?puesto={p.pk}",
    } for p in lista_puestos]
    return render(request, 'productores.html', {'puestos': lista_puestos, 'puntos': puntos})


@require_GET
@never_cache
def stock_publico(request):
    ids = [valor for valor in request.GET.get('ids', '').split(',') if valor]
    if not ids or len(ids) > 60 or not all(valor.isascii() and valor.isdecimal() and len(valor) <= 10 for valor in ids):
        return JsonResponse({'error': 'Publicaciones inválidas'}, status=400)
    productos = Producto.objects.filter(pk__in=ids).select_related('productor__puesto', 'productor__perfil')
    return JsonResponse({p.pk: datos_stock(p) for p in productos if p.vendedor_habilitado()})


def total_lista(usuario):
    return ItemCarrito.objects.filter(comprador=usuario, precio_unitario_acordado__isnull=True).count()


@login_required
def lista(request):
    # Cualquier cuenta puede comprar, tambien la de un vendedor
    items = list(ItemCarrito.objects.filter(comprador=request.user, precio_unitario_acordado__isnull=True)
                 .select_related('producto__productor__puesto', 'producto__productor__perfil', 'producto__categoria')
                 .order_by('producto__productor_id', '-fecha_agregado'))
    grupos = {}
    for item in items:
        puesto = getattr(item.producto.productor, 'puesto', None)
        grupo = grupos.setdefault(item.producto.productor_id, {'puesto': puesto, 'items': [], 'total': Decimal('0')})
        grupo['items'].append(item)
        if item.producto.esta_publicado():
            grupo['total'] += item.subtotal()
    return render(request, 'carrito.html', {
        'grupos': list(grupos.values()),
        'total_items': len(items),
        'total_estimado': sum((g['total'] for g in grupos.values()), Decimal('0')),
    })


@login_required
@require_POST
@transaction.atomic
def guardar_lista(request, producto_id):
    rapido = request.headers.get('X-Carrito-Rapido') == '1'
    producto = get_object_or_404(Producto.objects.publicados(), pk=producto_id)
    if producto.productor_id == request.user.id:
        texto = 'Este producto es de tu puesto: no hace falta agregarlo a tu lista.'
        if rapido:
            return JsonResponse({'ok': False, 'mensaje': texto}, status=400)
        messages.info(request, texto)
        return redirect('detalle_producto', producto_id=producto.pk)
    try:
        cantidad = forms.IntegerField(min_value=1, max_value=max(producto.stock, 1)).clean(request.POST.get('cantidad') or 1)
    except forms.ValidationError:
        if rapido:
            return JsonResponse({'ok': False, 'mensaje': f'Solo quedan {producto.stock} {producto.nombre_unidad_stock()}.'}, status=400)
        messages.warning(request, f'Solo quedan {producto.stock} {producto.nombre_unidad_stock()}. Ajusta la cantidad.')
        return redirect('detalle_producto', producto_id=producto.pk)
    ItemCarrito.objects.update_or_create(
        comprador=request.user, producto=producto, precio_unitario_acordado=None, defaults={'cantidad': cantidad},
    )
    texto = f'{producto.nombre}: {cantidad} {producto.unidad_corta()} en tu lista'
    if rapido:
        return JsonResponse({'ok': True, 'total_carrito': total_lista(request.user), 'mensaje': texto})
    messages.success(request, texto)
    if request.POST.get('volver') == 'detalle':
        return redirect('detalle_producto', producto_id=producto.pk)
    return redirect('carrito')


@login_required
@require_POST
def quitar_de_lista(request, item_id):
    item = get_object_or_404(ItemCarrito, pk=item_id, comprador=request.user)
    nombre = item.producto.nombre
    item.delete()
    messages.info(request, f'Quitaste {nombre} de tu lista.')
    return redirect('carrito')


# ---------------------------------------------------------------- vendedor

@login_required
@require_http_methods(['GET', 'POST'])
def quiero_vender(request):
    """Un comprador quiere vender: activa su puesto en la misma cuenta y sigue pudiendo comprar."""
    perfil = obtener_o_crear_perfil(request.user)
    if perfil.rol == 'PRODUCTOR':
        return redirect('panel_productor' if Puesto.objects.filter(vendedor=request.user).exists() else 'configurar_puesto')
    if request.method == 'POST':
        if request.POST.get('accion') == 'convertir':
            # La cuenta queda hibrida: vende en su puesto y conserva su lista, favoritos y mensajes
            perfil.rol = 'PRODUCTOR'
            perfil.save(update_fields=['rol'])
            messages.success(request, 'Listo, ahora puedes vender sin dejar de comprar. Marca en el mapa dónde está tu puesto.')
            return redirect('configurar_puesto')
        if request.POST.get('accion') == 'otra_cuenta':
            logout(request)
            return redirect(f"{reverse('registro')}?rol=PRODUCTOR")
    return render(request, 'quiero_vender.html', {'total_lista': total_lista(request.user)})


@login_required
@require_http_methods(['GET', 'POST'])
def configurar_puesto(request):
    if not es_vendedor(request.user):
        return redirect('quiero_vender')
    puesto = Puesto.objects.filter(vendedor=request.user).first() or Puesto(vendedor=request.user)
    nuevo = puesto.pk is None
    form = PuestoForm(request.POST if request.method == 'POST' else None, request.FILES or None, instance=puesto)
    if request.method == 'POST' and form.is_valid():
        form.save()
        if nuevo:
            messages.success(request, '¡Listo! Tu puesto ya aparece en el mapa. Ahora publica tu primer producto.')
            return redirect('crear_producto')
        messages.success(request, 'Guardaste los datos de tu puesto.')
        return redirect('panel_productor')
    return render(request, 'puesto_vendedor.html', {
        'form': form, 'puesto': puesto, 'nuevo': nuevo, 'maps_key': settings.GOOGLE_MAPS_API_KEY,
        'foto_actual': puesto.foto.url if puesto.foto else '',
        'campos_pago': [(form['efectivo'], 'bi-cash-coin'), (form['tarjeta'], 'bi-credit-card'), (form['yape_plin'], 'bi-phone')],
    })


def resumen_de_hoy(usuario):
    """Ventas que el vendedor marco hoy (hora de Lima) y cuanto suman."""
    ventas = VentaPuesto.objects.filter(vendedor=usuario, fecha__date=timezone.localdate())
    monto = ventas.aggregate(monto=Sum(F('cantidad') * F('precio_unitario')))['monto'] or Decimal('0')
    return ventas, Decimal(monto).quantize(Decimal('0.01'))


@login_required
def panel(request):
    if not es_vendedor(request.user):
        return redirect('carrito')
    puesto = Puesto.objects.filter(vendedor=request.user).first()
    productos = list(Producto.objects.filter(productor=request.user).select_related('categoria', 'productor__puesto', 'productor__perfil').order_by('-disponible', 'nombre'))
    ventas_hoy, vendido_hoy = resumen_de_hoy(request.user)
    interesados = (ItemCarrito.objects.filter(producto__productor=request.user, precio_unitario_acordado__isnull=True)
                   .values('producto_id').annotate(total=Count('id')))
    por_producto = {fila['producto_id']: fila['total'] for fila in interesados}
    for producto in productos:
        producto.interesados = por_producto.get(producto.pk, 0)
    return render(request, 'panel_productor.html', {
        'puesto': puesto,
        'productos': productos,
        'total_publicados': sum(1 for p in productos if p.esta_publicado()),
        'total_agotados': sum(1 for p in productos if p.stock == 0),
        'ventas_hoy': ventas_hoy.select_related('producto')[:20],
        'vendido_hoy': vendido_hoy,
        'unidades_hoy': ventas_hoy.count(),
        'total_interesados': sum(por_producto.values()),
    })


@login_required
@require_http_methods(['GET', 'POST'])
def publicar(request, producto_id=None):
    if not es_vendedor(request.user):
        return redirect('quiero_vender')
    puesto = Puesto.objects.filter(vendedor=request.user).first()
    if not puesto:
        messages.info(request, 'Primero marca en el mapa dónde está tu puesto.')
        return redirect('configurar_puesto')
    producto = (get_object_or_404(Producto, pk=producto_id, productor=request.user)
                if producto_id is not None else Producto(productor=request.user))
    form = PublicacionForm(request.POST if request.method == 'POST' else None, request.FILES or None, instance=producto)
    # Cuentas que el equipo agrego por dentro: sus ofertas salen sin pasar por el pago
    oferta_gratis = CuentaSinPagoOferta.incluye(request.user)
    if request.method == 'POST' and form.is_valid():
        antes = Producto.objects.filter(pk=producto.pk).values('stock', 'en_oferta').first() or {}
        stock_antes = antes.get('stock')
        producto = form.save(commit=False)
        producto.en_oferta = producto.precio_oferta is not None
        if not producto.en_oferta or oferta_gratis:
            producto.oferta_pendiente_pago = False
        elif not antes.get('en_oferta'):
            # Oferta nueva: sale como oferta cuando el vendedor paga la publicidad
            producto.oferta_pendiente_pago = True
        producto.oferta_inicio = producto.oferta_fin = None
        producto.acepta_ofertas = False
        producto.minimo_compra = 1
        producto.origen = puesto.nombre
        producto.fecha_vencimiento = fecha_vencimiento_por_defecto()
        if stock_antes != producto.stock:
            producto.stock_actualizado = timezone.now()
        producto.save()
        if producto.oferta_pendiente_pago:
            messages.info(request, f'Guardaste {producto.nombre}. Para que salga como oferta, paga la publicidad.')
            return redirect('pagar_comision_oferta', producto_id=producto.pk)
        messages.success(request, f'Guardaste {producto.nombre}. Ya se ve en la web.' if producto.esta_publicado()
                         else f'Guardaste {producto.nombre}.')
        return redirect('panel_productor')
    return render(request, 'form_producto.html', {
        'form': form, 'producto': producto, 'puesto': puesto,
        'foto_actual': producto.imagen.url if producto.imagen else '',
        'oferta_gratis': oferta_gratis,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def pagar_oferta(request, producto_id):
    """El vendedor paga (en modo demo) la publicidad para que su producto salga como oferta.
    No es una comision: la venta en el puesto no paga nada a AgroComercial."""
    if not es_vendedor(request.user):
        raise Http404()
    producto = get_object_or_404(Producto, pk=producto_id, productor=request.user)
    if not (producto.en_oferta and producto.oferta_pendiente_pago):
        messages.info(request, f'La oferta de {producto.nombre} no tiene pagos pendientes.')
        return redirect('panel_productor')
    if CuentaSinPagoOferta.incluye(request.user):
        Producto.objects.filter(pk=producto.pk).update(oferta_pendiente_pago=False)
        messages.success(request, f'{producto.nombre} ya sale en Ofertas. Tu cuenta no paga la publicidad.')
        return redirect('panel_productor')
    monto = producto.monto_comision_oferta()
    error = ''
    if request.method == 'POST':
        metodo = request.POST.get('metodo_pago', '')
        if metodo not in dict(PagoComision.METODOS):
            error = 'Elige si pagas con tarjeta o con QR.'
        else:
            with transaction.atomic():
                # El filtro evita registrar dos pagos si se presiona dos veces
                if Producto.objects.filter(pk=producto.pk, oferta_pendiente_pago=True).update(oferta_pendiente_pago=False):
                    pago = PagoComision.objects.create(
                        producto=producto, productor=request.user, porcentaje=Decimal('0'), monto=monto,
                        metodo_pago=metodo, codigo_transaccion=f'OF-{uuid.uuid4().hex[:10].upper()}',
                    )
                    messages.success(request, f'Pago demo de S/ {pago.monto} recibido (código {pago.codigo_transaccion}). '
                                              f'{producto.nombre} ya sale en Ofertas.')
            return redirect('panel_productor')
    return render(request, 'pagar_oferta.html', {
        'producto': producto, 'monto': monto, 'error': error,
        'metodo': request.POST.get('metodo_pago', 'TARJETA'),
    })


@login_required
@require_POST
def actualizar_stock(request, producto_id):
    """Cambia el stock desde el panel. Acepta formulario normal o fetch (responde JSON).
    accion: vendi (resta y registra la venta), sumar, fijar, agotado."""
    rapido = request.headers.get('X-Stock-Rapido') == '1'

    def responder(ok, texto, producto=None, estado=200, extra=None):
        if rapido:
            datos = {'ok': ok, 'mensaje': texto}
            if producto is not None:
                producto.refresh_from_db()
                datos.update(datos_stock(producto))
            datos.update(extra or {})
            return JsonResponse(datos, status=estado)
        (messages.success if ok else messages.warning)(request, texto)
        return redirect('panel_productor')

    if not es_vendedor(request.user):
        raise Http404()
    producto = get_object_or_404(Producto, pk=producto_id, productor=request.user)
    accion = request.POST.get('accion') or ('agotado' if request.POST.get('agotado') == '1' else 'fijar')
    entero = forms.IntegerField(min_value=0, max_value=2147483647)
    try:
        cantidad = entero.clean(request.POST.get('cantidad') or request.POST.get('stock') or (0 if accion == 'agotado' else None))
    except forms.ValidationError:
        return responder(False, 'Ingresa una cantidad entera igual o mayor a cero.', producto, 400)

    ahora = timezone.now()
    with transaction.atomic():
        if accion == 'vendi':
            if cantidad < 1:
                return responder(False, 'Indica cuánto vendiste.', producto, 400)
            vendidos = Producto.objects.filter(pk=producto.pk, stock__gte=cantidad).update(
                stock=F('stock') - cantidad, stock_actualizado=ahora)
            if not vendidos:
                return responder(False, f'No te quedan {cantidad} {producto.nombre_unidad_stock()}.', producto, 409)
            venta = VentaPuesto.objects.create(producto=producto, vendedor=request.user, cantidad=cantidad,
                                               precio_unitario=producto.precio_actual())
            ventas_hoy, vendido_hoy = resumen_de_hoy(request.user)
            # El panel usa estos totales tal cual; antes los sumaba en el navegador y se inflaban
            extra = {'venta_id': venta.pk, 'vendido_hoy': str(vendido_hoy), 'ventas_hoy': ventas_hoy.count(),
                     'total_venta': str(Decimal(venta.total()).quantize(Decimal('0.01')))}
            return responder(True, f'Vendiste {cantidad} {producto.unidad_corta()} de {producto.nombre}.', producto, extra=extra)
        elif accion == 'sumar':
            # Si llego mas mercaderia, la publicacion sigue visible otros dias
            Producto.objects.filter(pk=producto.pk).update(stock=F('stock') + cantidad, stock_actualizado=ahora,
                                                           fecha_vencimiento=fecha_vencimiento_por_defecto())
            texto = f'Agregaste {cantidad} a {producto.nombre}.'
        else:
            if accion == 'agotado':
                cantidad = 0
            anterior = request.POST.get('stock_anterior')
            filtro = Producto.objects.filter(pk=producto.pk)
            if anterior not in (None, ''):
                try:
                    filtro = filtro.filter(stock=entero.clean(anterior))
                except forms.ValidationError:
                    return responder(False, 'Cantidad anterior inválida.', producto, 400)
            if not filtro.update(stock=cantidad, stock_actualizado=ahora):
                return responder(False, 'El stock cambió en otra pantalla. Revisa el valor actual antes de guardarlo.', producto, 409)
            texto = f'{producto.nombre}: marcado como agotado.' if cantidad == 0 else f'{producto.nombre}: quedan {cantidad}.'
    return responder(True, texto, producto)


@login_required
@require_POST
def quitar_venta(request, venta_id):
    """Borra una venta de hoy marcada por error y devuelve las unidades al stock."""
    venta = get_object_or_404(VentaPuesto.objects.select_related('producto'), pk=venta_id, vendedor=request.user)
    destino = f"{reverse('panel_productor')}#tituloVentas"
    if timezone.localtime(venta.fecha).date() != timezone.localdate():
        messages.warning(request, 'Solo puedes quitar las ventas de hoy.')
        return redirect(destino)
    with transaction.atomic():
        Producto.objects.filter(pk=venta.producto_id).update(stock=F('stock') + venta.cantidad, stock_actualizado=timezone.now())
        venta.delete()
    messages.info(request, f'Quitaste la venta de {venta.cantidad} {venta.producto.unidad_corta()} de {venta.producto.nombre}. '
                           'Esas unidades volvieron a tu stock.')
    return redirect(destino)
