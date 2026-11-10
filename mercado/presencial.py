"""Vistas del mercado presencial: el vendedor publica lo que tiene en su puesto y el comprador
arma su lista, ve el stock en tiempo real y va al puesto a comprar (la compra se paga en el puesto).
El unico pago en la web es el de la publicidad de ofertas, por Yape/Plin al numero oficial."""
import logging
import re
from datetime import datetime, time, timedelta
from decimal import Decimal

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, F, Q, Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

import uuid

from .models import (
    Categoria, CompraTerminada, CuentaSinPagoOferta, ItemCarrito, Notificacion, PagoComision, Producto, Puesto, ResenaProducto,
    UbicacionVendedor, VentaPuesto,
    fecha_vencimiento_por_defecto,
)
from .forms import ResenaForm
from .seguridad import renombrar_imagen, tipo_de_imagen
from .views import asegurar_datos_iniciales, obtener_o_crear_perfil, ofertas_destacadas, con_precio_vigente

registro_pagos = logging.getLogger('mercado.pagos')

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
        # La foto ayuda pero no es obligatoria: asi el puesto queda guardado con solo marcar el mapa
        # y no se vuelve a pedir la ubicacion cada vez que se quiere publicar
        self.fields['foto'].required = False
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
    # Donde se vende: el puesto principal, una ubicacion guardada o una nueva que se marca aqui mismo
    donde = forms.ChoiceField(required=False, widget=forms.RadioSelect, label='¿Dónde lo vendes?')
    nueva_nombre = forms.CharField(
        label='Nombre de esta ubicación', max_length=100, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Feria del sábado en Cayma'}))
    nueva_referencia = forms.CharField(
        label='Referencia (opcional)', max_length=150, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. frente a la iglesia'}))
    nueva_direccion = forms.CharField(
        label='Dirección (opcional)', max_length=200, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Se llena sola al marcar el mapa'}))
    nueva_latitud = forms.DecimalField(max_digits=8, decimal_places=6, min_value=-90, max_value=90,
                                       required=False, widget=forms.HiddenInput())
    nueva_longitud = forms.DecimalField(max_digits=9, decimal_places=6, min_value=-180, max_value=180,
                                        required=False, widget=forms.HiddenInput())
    # Las dos fechas que elige el vendedor: desde cuando sale la oferta y cuando cree que se vence el producto
    fecha_oferta = forms.DateField(
        label='¿Desde qué día sale la oferta?', required=False,
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}))
    fecha_vence = forms.DateField(
        label='¿Qué día crees que se vence tu producto?', required=False,
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}))

    class Meta:
        model = Producto
        fields = ('nombre', 'categoria', 'descripcion', 'imagen', 'unidad', 'stock', 'fecha_cosecha', 'precio',
                  'precio_oferta', 'disponible')
        labels = {'fecha_cosecha': '¿Cuándo llegó a tu puesto?','nombre': '¿Qué vendes?', 'imagen': 'Foto del producto', 'precio': 'Precio normal (S/)',
                  'precio_oferta': 'Precio de oferta (S/)', 'disponible': 'Mostrar en la web',
                  'stock': 'Cantidad que tienes', 'unidad': 'Se vende por', 'descripcion': 'Descripción corta'}
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Palta fuerte'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Ej. Palta madura para hoy, de Majes.'}),
            'imagen': forms.FileInput(attrs={'accept': 'image/jpeg,image/png,image/webp', 'class': 'd-none'}),
            'unidad': forms.Select(attrs={'class': 'form-select'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'inputmode': 'numeric'}),
            'fecha_cosecha': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.10', 'min': '0.10', 'inputmode': 'decimal'}),
            'precio_oferta': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.10', 'min': '0.10', 'inputmode': 'decimal', 'placeholder': 'Opcional'}),
            'disponible': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
        }

    def __init__(self, *args, vendedor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].empty_label = 'Elige una categoría'
        self.fields['categoria'].queryset = Categoria.objects.order_by('nombre')
        self.fields['descripcion'].required = False
        # Con esta fecha se pinta la frescura (verde, amarillo o gris) en la tarjeta
        self.fields['fecha_cosecha'].required = False
        self.fields['fecha_cosecha'].widget.attrs['max'] = timezone.localdate().isoformat()
        actual = self.instance.unidad if self.instance and self.instance.pk else None
        self.fields['unidad'].choices = [c for c in Producto.UNIDADES if c[0] in UNIDADES_MERCADO or c[0] == actual]
        if not self.instance.pk:
            self.initial.setdefault('unidad', 'KG')
            self.initial.setdefault('disponible', True)
            self.initial.setdefault('fecha_cosecha', timezone.localdate())
        hoy = timezone.localdate()
        self.ultimo_dia = hoy + timedelta(days=settings.PUBLICACION_DIAS_MAXIMO)
        for campo in ('fecha_oferta', 'fecha_vence'):
            self.fields[campo].widget.attrs.update({'min': hoy.isoformat(), 'max': self.ultimo_dia.isoformat()})
        vence = inicio = None
        if self.instance.pk:
            if self.instance.fecha_vencimiento:
                vence = timezone.localtime(self.instance.fecha_vencimiento).date()
            if self.instance.oferta_inicio:
                inicio = timezone.localtime(self.instance.oferta_inicio).date()
        self.vence_por_defecto = hoy + timedelta(days=settings.PUBLICACION_DIAS_VIGENCIA)
        self.initial.setdefault('fecha_vence', vence if vence and vence >= hoy else self.vence_por_defecto)
        self.initial.setdefault('fecha_oferta', inicio if inicio and inicio > hoy else hoy)
        # Solo puede elegir sus propias ubicaciones
        self.ubicaciones = list(UbicacionVendedor.objects.filter(vendedor=vendedor)) if vendedor else []
        puesto = getattr(vendedor, 'puesto', None) if vendedor else None
        self.fields['donde'].choices = (
            [('puesto', puesto.nombre if puesto else 'Mi puesto')]
            + [(str(u.pk), u.nombre) for u in self.ubicaciones]
            + [('nueva', 'Agregar otra ubicación')]
        )
        guardada = self.instance.ubicacion_id if self.instance.pk else None
        self.initial.setdefault('donde', str(guardada) if guardada and any(u.pk == guardada for u in self.ubicaciones) else 'puesto')

    def ubicacion_elegida(self):
        """La UbicacionVendedor que eligio (None = puesto principal). Si es nueva, todavia no esta guardada."""
        donde = self.cleaned_data.get('donde')
        if donde == 'nueva':
            return UbicacionVendedor(
                vendedor=self.instance.productor, nombre=self.cleaned_data['nueva_nombre'].strip(),
                referencia=self.cleaned_data.get('nueva_referencia', '').strip(),
                direccion=self.cleaned_data.get('nueva_direccion', '').strip(),
                latitud=self.cleaned_data['nueva_latitud'], longitud=self.cleaned_data['nueva_longitud'],
            )
        return next((u for u in self.ubicaciones if str(u.pk) == donde), None)

    def clean_imagen(self):
        return validar_foto(self.cleaned_data['imagen'])

    def clean_fecha_cosecha(self):
        fecha = self.cleaned_data.get('fecha_cosecha') or timezone.localdate()
        if fecha > timezone.localdate():
            raise forms.ValidationError('La fecha de llegada no puede ser en el futuro.')
        return fecha

    def clean(self):
        datos = super().clean()
        precio = datos.get('precio')
        oferta = datos.get('precio_oferta')
        if precio is not None and precio <= 0:
            self.add_error('precio', 'Ingresa un precio mayor a cero.')
        if oferta is not None and (precio is None or not 0 < oferta < precio):
            self.add_error('precio_oferta', 'El precio de oferta debe ser menor al precio normal.')
        hoy = timezone.localdate()
        vence = datos.get('fecha_vence') or self.vence_por_defecto
        if 'fecha_vence' not in self.errors:
            if vence < hoy:
                self.add_error('fecha_vence', 'El día de vencimiento no puede ser un día que ya pasó.')
            elif vence > self.ultimo_dia:
                self.add_error('fecha_vence', f'Elige una fecha dentro de los próximos {settings.PUBLICACION_DIAS_MAXIMO} días.')
        inicio = datos.get('fecha_oferta') or hoy
        if oferta is not None and 'fecha_oferta' not in self.errors:
            if inicio < hoy:
                self.add_error('fecha_oferta', 'La oferta no puede empezar en un día que ya pasó.')
            elif inicio > vence:
                self.add_error('fecha_oferta', 'La oferta no puede empezar después del día en que se vence el producto.')
        datos['fecha_vence'], datos['fecha_oferta'] = vence, inicio
        datos['donde'] = datos.get('donde') or 'puesto'
        if datos['donde'] == 'nueva':
            if not (datos.get('nueva_nombre') or '').strip():
                self.add_error('nueva_nombre', 'Ponle un nombre a esta ubicación, así la reconoces después.')
            if datos.get('nueva_latitud') is None or datos.get('nueva_longitud') is None:
                self.add_error('donde', 'Marca en el mapa dónde queda la nueva ubicación.')
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
    publicados = Producto.objects.publicados().select_related('categoria', 'productor__puesto', 'productor__perfil', 'ubicacion')
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
        'total_ofertas': Producto.objects.ofertas_premium().count(),
        'total_puestos': puestos.count(),
    })


def catalogo(request, ofertas=False):
    asegurar_datos_iniciales()
    # La pagina Ofertas solo muestra las premium; las normales se ven en Productos con su etiqueta
    base = Producto.objects.ofertas_premium() if ofertas else Producto.objects.publicados()
    productos = con_precio_vigente(base.select_related('categoria', 'productor__puesto', 'productor__perfil', 'ubicacion'))
    busqueda = request.GET.get('q', '').strip()[:100]
    categoria_id = request.GET.get('categoria', '').strip()
    puesto_id = request.GET.get('puesto', '').strip()
    orden = request.GET.get('orden', 'recientes')
    if busqueda:
        productos = productos.filter(
            Q(nombre__icontains=busqueda) | Q(descripcion__icontains=busqueda)
            | Q(productor__puesto__nombre__icontains=busqueda) | Q(ubicacion__nombre__icontains=busqueda)
            | Q(categoria__nombre__icontains=busqueda)
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
        Producto.objects.select_related('productor__puesto', 'productor__perfil', 'categoria', 'ubicacion'), pk=producto_id)
    if request.user != producto.productor and not producto.vendedor_habilitado():
        raise Http404()
    en_lista = None
    if request.user.is_authenticated:
        en_lista = ItemCarrito.objects.filter(comprador=request.user, producto=producto,
                                              precio_unitario_acordado__isnull=True).first()
    mas_del_puesto = (Producto.objects.publicados().filter(productor=producto.productor)
                      .exclude(pk=producto.pk).select_related('categoria', 'productor__puesto', 'productor__perfil', 'ubicacion')[:4])
    resenas = ResenaProducto.objects.filter(producto=producto).select_related('autor__perfil')
    mi_resena = resenas.filter(autor=request.user).first() if request.user.is_authenticated else None
    promedio = resenas.aggregate(p=Avg('calificacion'))['p']
    return render(request, 'detalle_producto.html', {
        'producto': producto, 'puesto': getattr(producto.productor, 'puesto', None), 'lugar': producto.lugar(),
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
    # Otras ubicaciones de esos mismos vendedores que tienen productos publicados
    por_ubicacion = dict(Producto.objects.publicados().filter(ubicacion__isnull=False, productor__puesto__in=lista_puestos)
                         .order_by().values_list('ubicacion').annotate(total=Count('id')))
    for u in UbicacionVendedor.objects.filter(pk__in=por_ubicacion).select_related('vendedor__puesto'):
        puntos.append({
            'nombre': u.nombre, 'puesto': f'Otra ubicación de {u.vendedor.puesto.nombre}', 'productos': por_ubicacion[u.pk],
            'lat': float(u.latitud), 'lng': float(u.longitud), 'llegar': u.como_llegar(),
            'url': f"{reverse('catalogo')}?puesto={u.vendedor.puesto.pk}",
        })
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


def lista_agrupada(usuario):
    """Los productos de la lista y sus grupos: un grupo por cada lugar que hay que visitar."""
    items = list(ItemCarrito.objects.filter(comprador=usuario, precio_unitario_acordado__isnull=True)
                 .select_related('producto__productor__puesto', 'producto__productor__perfil', 'producto__categoria',
                                 'producto__ubicacion')
                 .order_by('producto__productor_id', '-fecha_agregado'))
    grupos = {}
    for item in items:
        # Un grupo por lugar: si el vendedor vende en dos ubicaciones, se ven como dos paradas
        lugar = item.producto.lugar()
        clave = (item.producto.productor_id, lugar.pk if isinstance(lugar, UbicacionVendedor) else None)
        grupo = grupos.setdefault(clave, {'puesto': lugar, 'items': [], 'total': Decimal('0')})
        grupo['items'].append(item)
        if item.producto.esta_publicado():
            grupo['total'] += item.subtotal()
    return items, list(grupos.values())


@login_required
def lista(request):
    # Cualquier cuenta puede comprar, tambien la de un vendedor
    items, grupos = lista_agrupada(request.user)
    return render(request, 'carrito.html', {
        'grupos': grupos,
        'total_items': len(items),
        'total_estimado': sum((g['total'] for g in grupos), Decimal('0')),
        'compras_terminadas': CompraTerminada.objects.filter(comprador=request.user)[:5],
    })


@login_required
@require_POST
@transaction.atomic
def terminar_compra(request):
    """El comprador ya fue al mercado: su lista se guarda en el historial y queda vacia.
    Solo toca su propia lista. No cobra nada ni cambia el stock (eso lo hace el vendedor con "Vendí")."""
    items, grupos = lista_agrupada(request.user)
    if not items:
        messages.info(request, 'Tu lista ya está vacía.')
        return redirect('carrito')
    detalle = [{
        'puesto': (g['puesto'].nombre if g['puesto'] else 'Puesto sin ubicación')[:100],
        'total': str(g['total'].quantize(Decimal('0.01'))),
        'items': [{
            'nombre': i.producto.nombre, 'cantidad': i.cantidad, 'unidad': i.producto.unidad_corta(),
            'precio': str(i.precio_aplicado()), 'subtotal': str(i.subtotal()),
        } for i in g['items']],
    } for g in grupos]
    total = sum((g['total'] for g in grupos), Decimal('0')).quantize(Decimal('0.01'))
    CompraTerminada.objects.create(comprador=request.user, total=total, productos=len(items), puestos=len(grupos), detalle=detalle)
    ItemCarrito.objects.filter(pk__in=[i.pk for i in items], comprador=request.user).delete()
    messages.success(request, f'Terminaste tu compra de S/ {total}. Tu lista quedó vacía y la guardamos en tus compras terminadas.')
    return redirect('carrito')


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
        'otras_ubicaciones': UbicacionVendedor.objects.filter(vendedor=request.user).annotate(total=Count('productos')),
    })


@login_required
@require_POST
def quitar_ubicacion(request, ubicacion_id):
    """Borra una ubicacion extra; sus productos vuelven a mostrarse en el puesto principal."""
    ubicacion = get_object_or_404(UbicacionVendedor, pk=ubicacion_id, vendedor=request.user)
    puesto = Puesto.objects.filter(vendedor=request.user).first()
    with transaction.atomic():
        Producto.objects.filter(ubicacion=ubicacion).update(ubicacion=None, origen=(puesto.nombre if puesto else '')[:120])
        ubicacion.delete()
    messages.info(request, f'Quitaste la ubicación "{ubicacion.nombre}". Sus productos ahora se ven en tu puesto principal.')
    return redirect(f"{reverse('configurar_puesto')}#otrasUbicaciones")


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
    productos = list(Producto.objects.filter(productor=request.user).select_related('categoria', 'productor__puesto', 'productor__perfil', 'ubicacion').order_by('-disponible', 'nombre'))
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
    form = PublicacionForm(request.POST if request.method == 'POST' else None, request.FILES or None, instance=producto,
                           vendedor=request.user)
    # Cuentas que el equipo agrego por dentro: sus ofertas salen sin pasar por el pago
    oferta_gratis = CuentaSinPagoOferta.incluye(request.user)
    if request.method == 'POST' and form.is_valid():
        antes = Producto.objects.filter(pk=producto.pk).values('stock', 'en_oferta').first() or {}
        stock_antes = antes.get('stock')
        producto = form.save(commit=False)
        producto.en_oferta = producto.precio_oferta is not None
        if not producto.en_oferta:
            producto.oferta_pendiente_pago = False
            producto.tipo_oferta = 'NORMAL'
        elif oferta_gratis:
            producto.oferta_pendiente_pago = False
            producto.tipo_oferta = 'PREMIUM'
        elif not antes.get('en_oferta'):
            # Oferta nueva: sale como oferta cuando el vendedor paga la publicidad (normal o premium)
            producto.oferta_pendiente_pago = True
        # La oferta dura hasta que el producto se vence; solo se guarda el inicio si es un dia que todavia no llega
        hoy = timezone.localdate()
        inicio = form.cleaned_data['fecha_oferta']
        producto.oferta_inicio = (timezone.make_aware(datetime.combine(inicio, time.min))
                                  if producto.en_oferta and inicio > hoy else None)
        producto.oferta_fin = None
        producto.acepta_ofertas = False
        producto.minimo_compra = 1
        ubicacion = form.ubicacion_elegida()
        if ubicacion is not None and ubicacion.pk is None:
            ubicacion.save()
            messages.info(request, f'Guardamos la ubicación "{ubicacion.nombre}". La próxima vez solo la eliges.')
        producto.ubicacion = ubicacion
        producto.origen = (ubicacion or puesto).nombre[:120]
        # Se muestra hasta el final del dia en que el vendedor cree que se vence
        producto.fecha_vencimiento = timezone.make_aware(datetime.combine(form.cleaned_data['fecha_vence'], time(23, 59, 59)))
        if stock_antes != producto.stock:
            producto.stock_actualizado = timezone.now()
        producto.save()
        if producto.oferta_pendiente_pago:
            messages.info(request, f'Guardaste {producto.nombre}. Para que salga como oferta, paga la publicidad por Yape o Plin.')
            return redirect('pagar_comision_oferta', producto_id=producto.pk)
        messages.success(request, f'Guardaste {producto.nombre}. Ya se ve en la web.' if producto.esta_publicado()
                         else f'Guardaste {producto.nombre}.')
        return redirect('panel_productor')
    return render(request, 'form_producto.html', {
        'form': form, 'producto': producto, 'puesto': puesto,
        'foto_actual': producto.imagen.url if producto.imagen else '',
        'oferta_gratis': oferta_gratis,
        'maps_key': settings.GOOGLE_MAPS_API_KEY,
    })


class PagoYapeForm(forms.Form):
    """Lo que escribe el vendedor despues de yapear: el plan, su numero de operacion y a nombre de quien esta su Yape.
    El monto y el numero de destino NO vienen del formulario: los pone el servidor."""
    tipo_oferta = forms.ChoiceField(choices=Producto.TIPOS_OFERTA, error_messages={
        'required': 'Elige si tu oferta es normal o premium.', 'invalid_choice': 'Elige si tu oferta es normal o premium.'})
    numero_operacion = forms.CharField(max_length=30, error_messages={'required': 'Escribe el número de operación de tu Yape o Plin.'})
    nombre_pagador = forms.CharField(min_length=3, max_length=80, error_messages={
        'required': 'Escribe el nombre que aparece en tu Yape o Plin.', 'min_length': 'Escribe el nombre que aparece en tu Yape o Plin.'})

    def clean_numero_operacion(self):
        numero = re.sub(r'[\s.\-]', '', self.cleaned_data['numero_operacion'])
        if not re.fullmatch(r'\d{6,15}', numero):
            raise forms.ValidationError('El número de operación solo tiene números (de 6 a 15). Cópialo tal cual sale en tu Yape o Plin.')
        return numero

    def clean_nombre_pagador(self):
        return ' '.join(self.cleaned_data['nombre_pagador'].split())


def telefono_pagos_legible():
    numero = settings.TELEFONO_PAGOS
    return ' '.join(numero[i:i + 3] for i in range(0, len(numero), 3))


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def pagar_oferta(request, producto_id):
    """El vendedor paga la publicidad por Yape o Plin al numero oficial y envia su numero de operacion.
    La oferta NO se publica aqui: queda en revision hasta que un administrador confirma el pago.
    No es una comision: la venta en el puesto no paga nada a MercOfertas."""
    if not es_vendedor(request.user):
        raise Http404()
    producto = get_object_or_404(Producto, pk=producto_id, productor=request.user)
    if CuentaSinPagoOferta.incluye(request.user) and producto.en_oferta and producto.oferta_pendiente_pago:
        Producto.objects.filter(pk=producto.pk).update(oferta_pendiente_pago=False, tipo_oferta='PREMIUM')
        messages.success(request, f'{producto.nombre} ya sale en Ofertas. Tu cuenta no paga la publicidad.')
        return redirect('panel_productor')
    base = {'producto': producto, 'telefono_pagos': telefono_pagos_legible(), 'titular_pagos': settings.TITULAR_PAGOS}
    en_revision = PagoComision.objects.filter(producto=producto, estado='PENDIENTE').first()
    if en_revision:
        return render(request, 'pagar_oferta.html', dict(base, en_revision=en_revision, monto=en_revision.monto))
    # Dos casos: oferta nueva sin pagar (elige normal o premium) u oferta normal que pasa a premium
    mejora = producto.puede_pasar_a_premium()
    if not (producto.en_oferta and producto.oferta_pendiente_pago) and not mejora:
        messages.info(request, f'La oferta de {producto.nombre} no tiene pagos pendientes.')
        return redirect('panel_productor')
    planes = [
        {'tipo': 'NORMAL', 'nombre': 'Oferta normal', 'monto': Producto.tarifa_oferta('NORMAL'),
         'detalle': 'Tu producto lleva la etiqueta "Oferta" en el listado de productos.'},
        {'tipo': 'PREMIUM', 'nombre': 'Oferta premium', 'monto': Producto.tarifa_oferta('PREMIUM'),
         'detalle': 'Además sale en el carrusel, en la página Ofertas y en el inicio.'},
    ]
    if mejora:
        planes = [dict(planes[1], nombre='Pasar a premium', monto=producto.diferencia_premium(),
                       detalle='Pagas solo la diferencia y tu oferta sale también en el carrusel, en Ofertas y en el inicio.')]
    tipo = request.POST.get('tipo_oferta') or request.GET.get('tipo') or 'PREMIUM'
    plan = next((p for p in planes if p['tipo'] == tipo), planes[-1])
    form = PagoYapeForm(request.POST if request.method == 'POST' else None)
    error = ''
    if request.method == 'POST':
        desde = timezone.now() - timedelta(hours=24)
        if not form.is_valid():
            error = ' '.join(mensaje for lista_errores in form.errors.values() for mensaje in lista_errores)
        elif not any(p['tipo'] == form.cleaned_data['tipo_oferta'] for p in planes):
            error = 'Elige si tu oferta es normal o premium.'
        elif PagoComision.objects.filter(productor=request.user, fecha_pago__gte=desde).count() >= settings.PAGOS_MAXIMO_POR_DIA:
            error = 'Ya enviaste varios pagos hoy. Espera a que los revisemos antes de enviar otro.'
            registro_pagos.warning('Limite diario de pagos alcanzado por el usuario %s', request.user.pk)
        elif PagoComision.objects.filter(numero_operacion=form.cleaned_data['numero_operacion']).exists():
            error = 'Ese número de operación ya fue registrado. Cada pago sirve para una sola oferta.'
            registro_pagos.warning('Numero de operacion repetido enviado por el usuario %s', request.user.pk)
        else:
            try:
                with transaction.atomic():
                    # Si se presiona dos veces, la segunda encuentra el pago ya en revision y no crea otro
                    if PagoComision.objects.filter(producto=producto, estado='PENDIENTE').exists():
                        return redirect('pagar_comision_oferta', producto_id=producto.pk)
                    pago = PagoComision.objects.create(
                        producto=producto, productor=request.user, porcentaje=Decimal('0'), monto=plan['monto'],
                        tipo_oferta=plan['tipo'], metodo_pago='YAPE_PLIN', estado='PENDIENTE',
                        codigo_transaccion=f'OF-{uuid.uuid4().hex[:10].upper()}',
                        numero_operacion=form.cleaned_data['numero_operacion'],
                        nombre_pagador=form.cleaned_data['nombre_pagador'],
                        telefono_destino=settings.TELEFONO_PAGOS,
                    )
            except IntegrityError:
                error = 'Ese número de operación ya fue registrado. Cada pago sirve para una sola oferta.'
            else:
                registro_pagos.info('Pago %s enviado a revision por el usuario %s (S/ %s)', pago.codigo_transaccion, request.user.pk, pago.monto)
                enlace = reverse('admin:mercado_pagocomision_changelist') + '?estado__exact=PENDIENTE'
                for admin_usuario in User.objects.filter(is_staff=True, is_active=True):
                    Notificacion.avisar(admin_usuario, f'Pago por revisar: S/ {pago.monto} de {request.user.username}, operación {pago.numero_operacion}.',
                                        enlace, 'bi-cash-coin')
                messages.success(request, f'Recibimos tu número de operación. Cuando confirmemos el pago, {producto.nombre} sale como oferta y te avisamos.')
                return redirect('pagar_comision_oferta', producto_id=producto.pk)
    ultimo = PagoComision.objects.filter(producto=producto).first()
    rechazado = ultimo if ultimo and ultimo.estado == 'RECHAZADO' else None
    return render(request, 'pagar_oferta.html', dict(
        base, planes=planes, plan=plan, monto=plan['monto'], mejora=mejora, error=error, form=form,
        rechazado=rechazado if rechazado and not error else None,
    ))


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
            # y vuelve a contar como fresco (llego hoy)
            Producto.objects.filter(pk=producto.pk).update(stock=F('stock') + cantidad, stock_actualizado=ahora,
                                                           fecha_cosecha=timezone.localdate(),
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
