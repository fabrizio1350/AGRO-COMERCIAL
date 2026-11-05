from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .models import ItemCarrito, Producto, Puesto, fecha_vencimiento_por_defecto
from .views import asegurar_datos_iniciales, obtener_o_crear_perfil


def validar_foto(archivo):
    if not archivo or not hasattr(archivo, 'content_type'):
        return archivo
    if archivo.size > 5 * 1024 * 1024:
        raise forms.ValidationError('La foto debe pesar como máximo 5 MB.')
    cabecera = archivo.read(12)
    archivo.seek(0)
    if not (cabecera.startswith((b'\xff\xd8\xff', b'\x89PNG\r\n\x1a\n'))
            or cabecera[:4] == b'RIFF' and cabecera[8:12] == b'WEBP'):
        raise forms.ValidationError('Selecciona una foto JPG, PNG o WEBP.')
    return archivo


class PuestoForm(forms.ModelForm):
    class Meta:
        model = Puesto
        fields = ('nombre', 'referencia', 'foto', 'latitud', 'longitud', 'efectivo', 'tarjeta', 'yape_plin')
        labels = {'nombre': 'Nombre del mercado o local', 'referencia': 'Puesto y referencia',
                  'foto': 'Foto del puesto', 'yape_plin': 'Yape / Plin'}
        help_texts = {'referencia': 'Ejemplo: puesto 24, pasillo de frutas.'}
        widgets = {'foto': forms.FileInput(attrs={'accept': 'image/jpeg,image/png,image/webp'})}

    def clean_foto(self):
        return validar_foto(self.cleaned_data['foto'])

    def clean(self):
        datos = super().clean()
        if not any(datos.get(campo) for campo in ('efectivo', 'tarjeta', 'yape_plin')):
            raise forms.ValidationError('Elige al menos una forma de pago en el puesto.')
        return datos


class PublicacionForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ('nombre', 'categoria', 'descripcion', 'imagen', 'unidad', 'stock', 'precio',
                  'precio_oferta', 'disponible')
        labels = {'imagen': 'Foto del producto', 'precio': 'Precio habitual (S/)',
                  'precio_oferta': 'Precio de oferta (S/, opcional)', 'disponible': 'Visible en el catálogo'}
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'imagen': forms.FileInput(attrs={'accept': 'image/jpeg,image/png,image/webp'}),
        }

    def clean_imagen(self):
        return validar_foto(self.cleaned_data['imagen'])

    def clean(self):
        datos = super().clean()
        precio = datos.get('precio')
        oferta = datos.get('precio_oferta')
        if precio is not None and precio <= 0:
            self.add_error('precio', 'Ingresa un precio mayor a cero.')
        if oferta is not None and (precio is None or not 0 < oferta < precio):
            self.add_error('precio_oferta', 'Ingresa un precio mayor a cero y menor al precio habitual.')
        return datos


def es_vendedor(usuario):
    return obtener_o_crear_perfil(usuario).rol == 'PRODUCTOR'


def vitrina(request, ofertas=False, portada=False):
    asegurar_datos_iniciales()
    productos = Producto.objects.ofertas_activas() if ofertas else Producto.objects.publicados()
    productos = productos.select_related('productor__perfil', 'productor__puesto', 'categoria')
    consulta = request.GET.get('q', '').strip()[:100]
    if consulta:
        productos = productos.filter(Q(nombre__icontains=consulta) | Q(productor__puesto__nombre__icontains=consulta))
    productos = productos.order_by('-en_oferta', '-fecha_publicacion', '-pk')
    return render(request, 'presencial/vitrina.html', {
        'pagina': Paginator(productos, 24).get_page(request.GET.get('page')),
        'consulta': consulta, 'ofertas': ofertas, 'portada': portada,
    })


def ficha(request, producto_id):
    producto = get_object_or_404(Producto.objects.select_related('productor__puesto', 'productor__perfil'), pk=producto_id)
    if request.user != producto.productor and not producto.vendedor_habilitado():
        raise Http404()
    return render(request, 'presencial/ficha.html', {'producto': producto})


@require_GET
@never_cache
def stock_publico(request):
    ids = request.GET.get('ids', '').split(',')
    if len(ids) > 40 or not all(valor.isascii() and valor.isdecimal() and len(valor) <= 10 for valor in ids):
        return JsonResponse({'error': 'Publicaciones inválidas'}, status=400)
    productos = Producto.objects.publicados().filter(pk__in=ids).select_related('productor__puesto', 'productor__perfil')
    return JsonResponse({p.pk: {'stock': p.stock, 'unidad': p.nombre_unidad_stock(),
                               'precio': str(p.precio_actual())} for p in productos})


@login_required
@require_http_methods(['GET', 'POST'])
def configurar_puesto(request):
    if not es_vendedor(request.user):
        raise Http404()
    puesto = Puesto.objects.filter(vendedor=request.user).first() or Puesto(vendedor=request.user)
    form = PuestoForm(request.POST if request.method == 'POST' else None, request.FILES, instance=puesto)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Guardaste la ubicación y los datos de tu puesto.')
        return redirect('panel_productor')
    return render(request, 'presencial/puesto.html', {'form': form, 'puesto': puesto, 'maps_key': settings.GOOGLE_MAPS_API_KEY})


@login_required
def panel(request):
    if not es_vendedor(request.user):
        return redirect('carrito')
    return render(request, 'presencial/panel.html', {
        'puesto': Puesto.objects.filter(vendedor=request.user).first(),
        'productos': Producto.objects.filter(productor=request.user),
    })


@login_required
@require_http_methods(['GET', 'POST'])
def publicar(request, producto_id=None):
    if not es_vendedor(request.user):
        raise Http404()
    puesto = Puesto.objects.filter(vendedor=request.user).first()
    if not puesto:
        messages.info(request, 'Configura tu puesto para que los compradores sepan dónde encontrarte.')
        return redirect('configurar_puesto')
    producto = (get_object_or_404(Producto, pk=producto_id, productor=request.user)
                if producto_id is not None else Producto(productor=request.user))
    form = PublicacionForm(request.POST if request.method == 'POST' else None, request.FILES, instance=producto)
    if request.method == 'POST' and form.is_valid():
        producto = form.save(commit=False)
        producto.en_oferta = producto.precio_oferta is not None
        producto.oferta_pendiente_pago = False
        producto.oferta_inicio = producto.oferta_fin = None
        producto.acepta_ofertas = False
        producto.minimo_compra = 1
        producto.origen = puesto.nombre
        producto.fecha_vencimiento = fecha_vencimiento_por_defecto()
        producto.save()
        messages.success(request, 'Guardaste el producto.')
        return redirect('panel_productor')
    return render(request, 'presencial/publicar.html', {'form': form, 'producto': producto})


@login_required
@require_POST
def actualizar_stock(request, producto_id):
    if not es_vendedor(request.user):
        raise Http404()
    producto = get_object_or_404(Producto, pk=producto_id, productor=request.user)
    campo = forms.IntegerField(min_value=0, max_value=2147483647)
    try:
        anterior = campo.clean(request.POST.get('stock_anterior'))
        cantidad = 0 if request.POST.get('agotado') == '1' else campo.clean(request.POST.get('stock'))
    except forms.ValidationError:
        messages.error(request, 'Ingresa una cantidad entera igual o mayor a cero.')
        return redirect('panel_productor')
    if Producto.objects.filter(pk=producto.pk, productor=request.user, stock=anterior).update(stock=cantidad):
        messages.success(request, 'Stock actualizado.')
    else:
        messages.warning(request, 'El stock cambió en otra pantalla. Revisa el valor actual antes de guardarlo.')
    return redirect('panel_productor')


@login_required
def lista(request):
    if es_vendedor(request.user):
        return redirect('panel_productor')
    items = ItemCarrito.objects.filter(comprador=request.user, precio_unitario_acordado__isnull=True)
    return render(request, 'presencial/lista.html', {
        'pagina': Paginator(items.select_related('producto__productor__puesto', 'producto__productor__perfil')
                            .order_by('-fecha_agregado'), 24).get_page(request.GET.get('page')),
    })


@login_required
@require_POST
@transaction.atomic
def guardar_lista(request, producto_id):
    if es_vendedor(request.user):
        raise Http404()
    producto = get_object_or_404(Producto.objects.publicados(), pk=producto_id)
    try:
        cantidad = forms.IntegerField(min_value=1, max_value=producto.stock).clean(request.POST.get('cantidad'))
    except forms.ValidationError:
        messages.warning(request, 'Revisa la cantidad disponible y vuelve a intentarlo.')
        return redirect('detalle_producto', producto_id=producto.pk)
    ItemCarrito.objects.update_or_create(
        comprador=request.user, producto=producto, precio_unitario_acordado=None, defaults={'cantidad': cantidad},
    )
    messages.success(request, 'Guardaste el producto en tu lista.')
    return redirect('carrito')
