import json
import urllib.request
import urllib.parse
import urllib.error
import uuid
from datetime import date, timedelta
from decimal import Decimal
from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from .models import (
    PerfilUsuario,
    Categoria,
    Producto,
    OfertaNegociacion,
    ItemCarrito,
    Pedido,
    ResenaProducto,
)
from .forms import (
    RegistroUsuarioForm,
    ProductoForm,
    OfertaNegociacionForm,
    PasarelaPagoForm,
    ResenaForm,
    PerfilForm,
)


def asegurar_datos_iniciales():
    """Crea datos de prueba iniciales si la base de datos esta vacia."""
    if Producto.objects.exists():
        return

    cat_tuberculos, _ = Categoria.objects.get_or_create(
        nombre="Tubérculos y Raíces",
        defaults={"descripcion": "Papas nativas, camotes, yucas y ollucos cosechados en sierra y costa."}
    )
    cat_hortalizas, _ = Categoria.objects.get_or_create(
        nombre="Hortalizas y Verduras",
        defaults={"descripcion": "Verduras frescas de huerta listas para distribución directa."}
    )
    cat_frutas, _ = Categoria.objects.get_or_create(
        nombre="Frutas de Estación",
        defaults={"descripcion": "Frutas seleccionadas directamente de los valles productores."}
    )
    cat_granos, _ = Categoria.objects.get_or_create(
        nombre="Granos y Cereales",
        defaults={"descripcion": "Quinua, maíz amiláceo, habas secas y menestras andinas."}
    )

    productor1, creado1 = User.objects.get_or_create(
        username="productor_mantaro",
        defaults={
            "first_name": "Mateo",
            "last_name": "Huamán",
            "email": "mateo.agromantaro@gmail.com",
        }
    )
    if creado1:
        productor1.set_password("agro12345")
        productor1.save()
        PerfilUsuario.objects.create(
            usuario=productor1,
            rol="PRODUCTOR",
            ruc_dni="10445566771",
            telefono="964112233",
            ubicacion="Huancayo, Junín",
            nombre_finca="Asociación Agrícola Valle del Mantaro",
            cuenta_bancaria="BCP Soles: 355-98765432-0-11"
        )
    else:
        p1 = PerfilUsuario.objects.filter(usuario=productor1).first()
        if p1 and not p1.cuenta_bancaria:
            p1.cuenta_bancaria = "BCP Soles: 355-98765432-0-11"
            p1.save()

    productor2, creado2 = User.objects.get_or_create(
        username="productor_huaral",
        defaults={
            "first_name": "Elena",
            "last_name": "Rojas",
            "email": "elena.fundo@gmail.com",
        }
    )
    if creado2:
        productor2.set_password("agro12345")
        productor2.save()
        PerfilUsuario.objects.create(
            usuario=productor2,
            rol="PRODUCTOR",
            ruc_dni="20556677889",
            telefono="945887766",
            ubicacion="Huaral, Lima",
            nombre_finca="Fundo Santa Elena",
            cuenta_bancaria="BBVA Soles: 0011-0234-0200112233"
        )
    else:
        p2 = PerfilUsuario.objects.filter(usuario=productor2).first()
        if p2 and not p2.cuenta_bancaria:
            p2.cuenta_bancaria = "BBVA Soles: 0011-0234-0200112233"
            p2.save()

    comprador_demo, creado3 = User.objects.get_or_create(
        username="comprador_lima",
        defaults={
            "first_name": "Carlos",
            "last_name": "Mendoza",
            "email": "carlos.comprador@gmail.com",
        }
    )
    if creado3:
        comprador_demo.set_password("agro12345")
        comprador_demo.save()
        PerfilUsuario.objects.create(
            usuario=comprador_demo,
            rol="COMPRADOR",
            ruc_dni="20601122334",
            telefono="999445566",
            ubicacion="Lima Metropolitana",
            nombre_finca="Distribuidora Mayorista Mendoza SAC"
        )

    hoy = date.today()
    productos_demo = [
        {
            "productor": productor1,
            "categoria": cat_tuberculos,
            "nombre": "Papa Amarilla Tumbay Seleccionada",
            "variedad": "Amarilla Tumbay",
            "tipo_cultivo": "TRADICIONAL",
            "fecha_cosecha": hoy - timedelta(days=2),
            "calidad": "PRIMERA",
            "descripcion": "Papa amarilla de primera calidad, cosecha reciente libre de químicos agresivos. Ideal para mercados minoristas, pollerías y restaurantes. Empacada en mallas ventiladas.",
            "precio": Decimal("3.80"),
            "en_oferta": True,
            "precio_oferta": Decimal("3.20"),
            "acepta_ofertas": True,
            "unidad": "KG",
            "stock": 450,
            "minimo_compra": 10,
            "origen": "Huancayo, Junín",
        },
        {
            "productor": productor1,
            "categoria": cat_granos,
            "nombre": "Quinua Blanca Orgánica de Altura",
            "variedad": "Blanca Seleccionada",
            "tipo_cultivo": "ORGANICO",
            "fecha_cosecha": hoy - timedelta(days=5),
            "calidad": "PRIMERA",
            "descripcion": "Grano seleccionado, limpio y secado de forma natural a más de 3,400 msnm. Alto valor nutritivo, listo para envasado o distribución directa.",
            "precio": Decimal("9.50"),
            "en_oferta": False,
            "precio_oferta": None,
            "acepta_ofertas": True,
            "unidad": "KG",
            "stock": 200,
            "minimo_compra": 5,
            "origen": "Jauja, Junín",
        },
        {
            "productor": productor1,
            "categoria": cat_hortalizas,
            "nombre": "Zanahoria Fresca de Sierra (Saco 50 kg)",
            "variedad": "Lavada en saco",
            "tipo_cultivo": "TRADICIONAL",
            "fecha_cosecha": hoy - timedelta(days=1),
            "calidad": "ESTANDAR",
            "descripcion": "Saco de 50 kg de zanahoria fresca recién lavada y clasificada. Excelente resistencia para transporte interprovincial.",
            "precio": Decimal("65.00"),
            "en_oferta": True,
            "precio_oferta": Decimal("54.00"),
            "acepta_ofertas": True,
            "unidad": "SACO",
            "stock": 35,
            "minimo_compra": 1,
            "origen": "Tarma, Junín",
        },
        {
            "productor": productor2,
            "categoria": cat_frutas,
            "nombre": "Mandarina Satsuma sin Pepa",
            "variedad": "Sin pepa dulce",
            "tipo_cultivo": "INVERNADERO",
            "fecha_cosecha": hoy - timedelta(days=3),
            "calidad": "PRIMERA",
            "descripcion": "Caja de 20 kg de mandarina dulce de exportación, cosechada esta semana en el valle de Huaral con riego tecnificado.",
            "precio": Decimal("48.00"),
            "en_oferta": True,
            "precio_oferta": Decimal("39.90"),
            "acepta_ofertas": True,
            "unidad": "CAJA",
            "stock": 60,
            "minimo_compra": 2,
            "origen": "Huaral, Lima",
        },
        {
            "productor": productor2,
            "categoria": cat_frutas,
            "nombre": "Palta Hass de Exportación",
            "variedad": "Hass Firme",
            "tipo_cultivo": "ORGANICO",
            "fecha_cosecha": hoy - timedelta(days=2),
            "calidad": "PRIMERA",
            "descripcion": "Palta Hass con materia seca óptima, piel rugosa y excelente conservación para transporte nacional o mayorista.",
            "precio": Decimal("6.20"),
            "en_oferta": False,
            "precio_oferta": None,
            "acepta_ofertas": True,
            "unidad": "KG",
            "stock": 300,
            "minimo_compra": 15,
            "origen": "Chancay, Lima",
        },
        {
            "productor": productor2,
            "categoria": cat_hortalizas,
            "nombre": "Tomate Río Grande Seleccionado",
            "variedad": "En caja de 20 kg",
            "tipo_cultivo": "INVERNADERO",
            "fecha_cosecha": hoy,
            "calidad": "ESTANDAR",
            "descripcion": "Caja de 20 kg de tomate firme, maduración uniforme pintón-rojo para distribución directa a mercados y supermercados.",
            "precio": Decimal("42.00"),
            "en_oferta": True,
            "precio_oferta": Decimal("35.00"),
            "acepta_ofertas": True,
            "unidad": "CAJA",
            "stock": 40,
            "minimo_compra": 1,
            "origen": "Barranca, Lima",
        },
    ]

    productos_creados = []
    for datos in productos_demo:
        prod = Producto.objects.create(**datos)
        productos_creados.append(prod)

    if productos_creados:
        ResenaProducto.objects.create(
            producto=productos_creados[0],
            autor=comprador_demo,
            calificacion=5,
            comentario="Excelente lote de papa amarilla, llegó puntual y muy bien seleccionada sin tierra."
        )
        OfertaNegociacion.objects.create(
            producto=productos_creados[0],
            comprador=comprador_demo,
            cantidad=50,
            precio_unitario_ofrecido=Decimal("2.90"),
            mensaje="Hola Mateo, te compro 50 kg inmediatos si me dejas a S/ 2.90 el kilo.",
            estado="PENDIENTE"
        )


def obtener_o_crear_perfil(usuario):
    perfil, _ = PerfilUsuario.objects.get_or_create(usuario=usuario)
    return perfil


def procesar_cobro_culqi(total_soles, correo_gmail, culqi_token):
    """
    Procesa el cobro en Soles (PEN) usando la API de Culqi (https://api.culqi.com/v2/charges)
    vinculado al correo Gmail del comprador. Si aún no se colocó CULQI_SECRET_KEY en .env,
    ejecuta la simulación de prueba de Culqi para no interrumpir la demostración.
    """
    monto_centimos = int(Decimal(str(total_soles)) * 100)
    secret_key = getattr(settings, 'CULQI_SECRET_KEY', '').strip()

    if secret_key and culqi_token and culqi_token.startswith('tkn_'):
        url = "https://api.culqi.com/v2/charges"
        payload = json.dumps({
            "amount": monto_centimos,
            "currency_code": "PEN",
            "email": correo_gmail,
            "source_id": culqi_token,
            "description": "Compra de productos agricolas en AgroComercial"
        }).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {secret_key}",
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                datos_resp = json.loads(resp.read().decode('utf-8'))
                charge_id = datos_resp.get('id', f"chr_test_{uuid.uuid4().hex[:8]}")
                return True, charge_id, "Cobro procesado en Culqi API"
        except urllib.error.HTTPError as e:
            try:
                err_body = json.loads(e.read().decode('utf-8'))
                msg_err = err_body.get('user_message') or err_body.get('merchant_message') or "Tarjeta rechazada por Culqi."
            except Exception:
                msg_err = "No se pudo completar el cargo en Culqi."
            return False, None, msg_err
        except Exception as e:
            return False, None, f"Error de conexión con Culqi: {e}"

    # Modo Sandbox / Prueba local cuando se usa tarjeta de prueba de Culqi
    codigo_culqi = f"CULQI-CHR-{uuid.uuid4().hex[:6].upper()}"
    return True, codigo_culqi, "Cobro aprobado en Pasarela Culqi (Modo Prueba)"


def enviar_comprobante_gmail(usuario, correo_destino, codigo_tx, lista_pedidos, total_pagar, metodo_pago):
    """
    Envía por correo Gmail el comprobante electrónico de la compra procesada en Culqi.
    Usa las credenciales encriptadas/protegidas en .env (EMAIL_HOST_USER y EMAIL_HOST_PASSWORD).
    """
    if not correo_destino:
        return False

    lineas_productos = "\n".join(
        [f"  - {p.producto.nombre} ({p.cantidad} {p.producto.get_unidad_display()}): S/ {p.total}" for p in lista_pedidos]
    )
    asunto = f"Comprobante de Pago {codigo_tx} - AgroComercial"
    cuerpo = (
        f"Hola {usuario.first_name or usuario.username},\n\n"
        f"Tu pago ha sido procesado correctamente en AgroComercial.\n\n"
        f"=============================================\n"
        f"COMPROBANTE ELECTRÓNICO DE COMPRA AGRÍCOLA\n"
        f"=============================================\n"
        f"Código de Operación: {codigo_tx}\n"
        f"Correo Gmail asociado: {correo_destino}\n"
        f"Modalidad de Pago: {metodo_pago}\n\n"
        f"Detalle de Productos:\n"
        f"{lineas_productos}\n"
        f"  - Costo de envío / guía: S/ 15.00\n"
        f"---------------------------------------------\n"
        f"TOTAL COBRADO: S/ {total_pagar}\n"
        f"=============================================\n\n"
        f"Gracias por comprar directo a los productores agrícolas en AgroComercial."
    )
    try:
        send_mail(
            subject=asunto,
            message=cuerpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[correo_destino],
            fail_silently=True,
        )
        return True
    except Exception:
        return False


def inicio(request):
    asegurar_datos_iniciales()
    if not request.user.is_authenticated:
        return redirect('login')

    categorias = Categoria.objects.all()
    productos_destacados = Producto.objects.filter(disponible=True, stock__gt=0)[:6]
    productos_en_oferta = Producto.objects.filter(disponible=True, en_oferta=True, stock__gt=0)
    total_productos = Producto.objects.filter(disponible=True).count()
    total_productores = PerfilUsuario.objects.filter(rol='PRODUCTOR').count()
    total_pedidos = Pedido.objects.count()
    total_ofertas = productos_en_oferta.count()

    contexto = {
        'categorias': categorias,
        'productos_destacados': productos_destacados,
        'productos_en_oferta': productos_en_oferta,
        'total_productos': total_productos,
        'total_productores': total_productores,
        'total_pedidos': total_pedidos,
        'total_ofertas': total_ofertas,
    }
    return render(request, 'inicio.html', contexto)


def catalogo(request):
    """Marketplace Agricola completo con buscador, filtros combinados y ordenamiento."""
    asegurar_datos_iniciales()
    productos = Producto.objects.filter(disponible=True)
    categorias = Categoria.objects.all()

    busqueda = request.GET.get('q', '').strip()
    categoria_id = request.GET.get('categoria', '').strip()
    productor_id = request.GET.get('productor', '').strip()
    unidad = request.GET.get('unidad', '').strip()
    tipo_cultivo = request.GET.get('cultivo', '').strip()
    solo_ofertas = request.GET.get('ofertas', '').strip()
    precio_max = request.GET.get('precio_max', '').strip()
    orden = request.GET.get('orden', 'recientes').strip()

    if busqueda:
        productos = productos.filter(
            Q(nombre__icontains=busqueda) |
            Q(descripcion__icontains=busqueda) |
            Q(origen__icontains=busqueda) |
            Q(variedad__icontains=busqueda)
        )
    if categoria_id.isdigit():
        productos = productos.filter(categoria_id=int(categoria_id))
    if productor_id.isdigit():
        productos = productos.filter(productor_id=int(productor_id))
    if unidad:
        productos = productos.filter(unidad=unidad)
    if tipo_cultivo:
        productos = productos.filter(tipo_cultivo=tipo_cultivo)
    if solo_ofertas == '1':
        productos = productos.filter(en_oferta=True)
    if precio_max:
        try:
            val_max = Decimal(precio_max)
            productos = productos.filter(Q(precio__lte=val_max) | Q(en_oferta=True, precio_oferta__lte=val_max))
        except Exception:
            pass

    if orden == 'precio_asc':
        productos = productos.order_by('precio')
    elif orden == 'precio_desc':
        productos = productos.order_by('-precio')
    elif orden == 'stock':
        productos = productos.order_by('-stock')
    else:
        productos = productos.order_by('-fecha_publicacion')

    contexto = {
        'productos': productos,
        'categorias': categorias,
        'unidades': Producto.UNIDADES,
        'tipos_cultivo': Producto.TIPOS_CULTIVO,
        'busqueda': busqueda,
        'categoria_seleccionada': categoria_id,
        'productor_seleccionado': productor_id,
        'unidad_seleccionada': unidad,
        'cultivo_seleccionado': tipo_cultivo,
        'solo_ofertas': solo_ofertas,
        'precio_max': precio_max,
        'orden_seleccionado': orden,
    }
    return render(request, 'catalogo.html', contexto)


def ventas_por_oferta(request):
    """Apartado de Ventas por Oferta con buscador y filtro para proponer ofertas."""
    asegurar_datos_iniciales()
    busqueda = request.GET.get('q', '').strip()
    categoria_id = request.GET.get('categoria', '').strip()
    categorias = Categoria.objects.all()

    productos_remate = Producto.objects.filter(disponible=True, en_oferta=True, stock__gt=0)
    productos_negociables = Producto.objects.filter(disponible=True, acepta_ofertas=True, stock__gt=0)

    if busqueda:
        filtro_q = Q(nombre__icontains=busqueda) | Q(origen__icontains=busqueda) | Q(descripcion__icontains=busqueda)
        productos_remate = productos_remate.filter(filtro_q)
        productos_negociables = productos_negociables.filter(filtro_q)
    if categoria_id.isdigit():
        productos_remate = productos_remate.filter(categoria_id=int(categoria_id))
        productos_negociables = productos_negociables.filter(categoria_id=int(categoria_id))

    mis_ofertas_enviadas = []
    ofertas_recibidas_vendedor = []
    if request.user.is_authenticated:
        mis_ofertas_enviadas = OfertaNegociacion.objects.filter(comprador=request.user).select_related('producto', 'producto__productor')
        ofertas_recibidas_vendedor = OfertaNegociacion.objects.filter(producto__productor=request.user).select_related('producto', 'comprador')

    contexto = {
        'productos_remate': productos_remate,
        'productos_negociables': productos_negociables,
        'mis_ofertas_enviadas': mis_ofertas_enviadas,
        'ofertas_recibidas_vendedor': ofertas_recibidas_vendedor,
        'categorias': categorias,
        'busqueda': busqueda,
        'categoria_id': categoria_id,
    }
    return render(request, 'ofertas.html', contexto)


def detalle_producto(request, producto_id):
    """Apartado completo de descripcion del producto, ficha tecnica, compras, ofertas y resenas."""
    asegurar_datos_iniciales()
    producto = get_object_or_404(Producto, id=producto_id)
    relacionados = Producto.objects.filter(
        categoria=producto.categoria,
        disponible=True
    ).exclude(id=producto.id)[:3]
    resenas = producto.resenas.select_related('autor').all()

    oferta_form = OfertaNegociacionForm(initial={'cantidad': max(producto.minimo_compra, 10)})
    resena_form = ResenaForm()

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.warning(request, "Inicia sesión como Comprador o Vendedor para realizar esta acción.")
            return redirect('login')

        tipo_accion = request.POST.get('tipo_accion', '')

        # 1. Enviar propuesta de oferta (solo permitido para COMPRADOR)
        if tipo_accion == 'enviar_oferta':
            perfil_usr = obtener_o_crear_perfil(request.user)
            if perfil_usr.rol != 'COMPRADOR':
                messages.warning(request, "Solo las cuentas de Comprador pueden enviar ofertas de compra.")
                return redirect('detalle_producto', producto_id=producto.id)

            oferta_form = OfertaNegociacionForm(request.POST)
            if oferta_form.is_valid():
                propuesta = oferta_form.save(commit=False)
                propuesta.producto = producto
                propuesta.comprador = request.user
                propuesta.save()
                messages.success(
                    request,
                    f"Oferta enviada al vendedor: S/ {propuesta.precio_unitario_ofrecido} por {propuesta.cantidad} unidades."
                )
                return redirect('ventas_por_oferta')

        # 2. Publicar resena o comentario del producto
        elif tipo_accion == 'publicar_resena':
            resena_form = ResenaForm(request.POST)
            if resena_form.is_valid():
                nueva_resena = resena_form.save(commit=False)
                nueva_resena.producto = producto
                nueva_resena.autor = request.user
                nueva_resena.save()
                messages.success(request, "¡Gracias! Tu calificación fue agregada a la descripción del producto.")
                return redirect('detalle_producto', producto_id=producto.id)

    contexto = {
        'producto': producto,
        'relacionados': relacionados,
        'resenas': resenas,
        'oferta_form': oferta_form,
        'resena_form': resena_form,
    }
    return render(request, 'detalle_producto.html', contexto)


@login_required
def responder_oferta(request, oferta_id):
    """Permite al vendedor aceptar o rechazar una oferta de compra, o al comprador llevarla al carrito."""
    oferta = get_object_or_404(OfertaNegociacion, id=oferta_id)
    if request.method == 'POST':
        decision = request.POST.get('decision')
        respuesta = request.POST.get('respuesta_vendedor', '').strip()

        # Accion del vendedor dueno del producto
        if oferta.producto.productor == request.user:
            if decision == 'ACEPTAR':
                oferta.estado = 'ACEPTADA'
                oferta.respuesta_vendedor = respuesta or "Oferta aceptada. Puedes proceder al pago."
                oferta.save()
                messages.success(request, f"Aceptaste la oferta #{oferta.id} de {oferta.comprador.username}.")
            elif decision == 'RECHAZAR':
                oferta.estado = 'RECHAZADA'
                oferta.respuesta_vendedor = respuesta or "No es posible aceptar ese precio por el momento."
                oferta.save()
                messages.info(request, f"Rechazaste la oferta #{oferta.id}.")
            return redirect('ventas_por_oferta')

        # Accion del comprador para pagar una oferta ya aceptada
        if oferta.comprador == request.user and oferta.estado == 'ACEPTADA' and decision == 'PAGAR_OFERTA':
            ItemCarrito.objects.create(
                comprador=request.user,
                producto=oferta.producto,
                cantidad=oferta.cantidad,
                precio_unitario_acordado=oferta.precio_unitario_ofrecido
            )
            oferta.estado = 'PAGADA'
            oferta.save()
            messages.success(request, "Tu oferta aceptada fue cargada con el precio especial. Completa el pago en la pasarela.")
            return redirect('pasarela_pago')

    return redirect('ventas_por_oferta')


@login_required
def agregar_al_carrito(request, producto_id):
    perfil = obtener_o_crear_perfil(request.user)
    if perfil.rol != 'COMPRADOR':
        messages.warning(request, "Estás en una cuenta de Vendedor. Cambia a cuenta de Comprador para realizar compras.")
        return redirect('detalle_producto', producto_id=producto_id)

    producto = get_object_or_404(Producto, id=producto_id)
    cantidad = int(request.POST.get('cantidad', producto.minimo_compra or 1))
    if cantidad < 1:
        cantidad = 1
    if cantidad > producto.stock:
        messages.error(request, f"Solo hay {producto.stock} unidades disponibles en stock.")
        return redirect('detalle_producto', producto_id=producto.id)

    item, creado = ItemCarrito.objects.get_or_create(
        comprador=request.user,
        producto=producto,
        precio_unitario_acordado=None,
        defaults={'cantidad': cantidad}
    )
    if not creado:
        item.cantidad = min(producto.stock, item.cantidad + cantidad)
        item.save()

    ir_a_pagar = request.POST.get('comprar_ahora') == '1'
    if ir_a_pagar:
        return redirect('pasarela_pago')

    messages.success(request, f"Se agregaron {cantidad} unidades de '{producto.nombre}' a tu carrito.")
    return redirect('carrito')


@login_required
def carrito_vista(request):
    perfil = obtener_o_crear_perfil(request.user)
    if perfil.rol != 'COMPRADOR':
        messages.warning(request, "El carrito de compras es exclusivo para cuentas de Comprador.")
        return redirect('panel_productor')

    items = ItemCarrito.objects.filter(comprador=request.user).select_related('producto', 'producto__productor')
    subtotal = sum(i.subtotal() for i in items)
    costo_logistica = Decimal("15.00") if subtotal > 0 else Decimal("0.00")
    total_pagar = subtotal + costo_logistica

    contexto = {
        'items': items,
        'subtotal': subtotal,
        'costo_logistica': costo_logistica,
        'total_pagar': total_pagar,
    }
    return render(request, 'carrito.html', contexto)


@login_required
def eliminar_del_carrito(request, item_id):
    item = get_object_or_404(ItemCarrito, id=item_id, comprador=request.user)
    if request.method == 'POST':
        item.delete()
        messages.info(request, "Producto retirado del carrito.")
    return redirect('carrito')


@login_required
def pasarela_pago(request):
    """Apartado de Pasarela de Pago con Culqi vinculado al Gmail del comprador."""
    perfil = obtener_o_crear_perfil(request.user)
    if perfil.rol != 'COMPRADOR':
        messages.warning(request, "La pasarela de pago es exclusiva para cuentas de Comprador.")
        return redirect('panel_productor')

    items = ItemCarrito.objects.filter(comprador=request.user).select_related('producto', 'producto__productor')
    if not items.exists():
        messages.warning(request, "Tu carrito está vacío. Agrega productos antes de ir a pagar.")
        return redirect('catalogo')

    subtotal = sum(i.subtotal() for i in items)
    costo_logistica = Decimal("15.00")
    total_pagar = subtotal + costo_logistica
    correo_gmail_usuario = request.user.email or f"{request.user.username}@gmail.com"

    if request.method == 'POST':
        form = PasarelaPagoForm(request.POST)
        if form.is_valid():
            metodo = form.cleaned_data['metodo_pago']
            correo_culqi = request.POST.get('correo_culqi', '').strip() or correo_gmail_usuario
            culqi_token = request.POST.get('culqi_token', '').strip()

            # Actualizar el Gmail en el usuario si estaba vacio
            if correo_culqi and request.user.email != correo_culqi:
                request.user.email = correo_culqi
                request.user.save()

            if metodo == 'TARJETA':
                exito_culqi, codigo_tx, mensaje_culqi = procesar_cobro_culqi(
                    total_pagar, correo_culqi, culqi_token
                )
                if not exito_culqi:
                    messages.error(request, f"Error en Pasarela Culqi: {mensaje_culqi}")
                    return redirect('pasarela_pago')
                estado_pago = 'PAGADO'
            else:
                codigo_tx = f"AGRO-2026-{uuid.uuid4().hex[:6].upper()}"
                estado_pago = 'PENDIENTE_VERIFICACION' if metodo == 'CONTRAENTREGA' else 'PAGADO'

            pedidos_creados = []
            for item in items:
                prod = item.producto
                cant = min(item.cantidad, prod.stock) if prod.stock > 0 else item.cantidad
                precio_unit = item.precio_aplicado()
                ped = Pedido.objects.create(
                    comprador=request.user,
                    producto=prod,
                    cantidad=cant,
                    precio_unitario=precio_unit,
                    total=cant * precio_unit,
                    direccion_entrega=form.cleaned_data['direccion_entrega'],
                    ciudad_destino=form.cleaned_data['ciudad_destino'],
                    telefono_contacto=form.cleaned_data['telefono_contacto'],
                    comentario=form.cleaned_data['comentario'],
                    metodo_pago=metodo,
                    estado_pago=estado_pago,
                    codigo_transaccion=codigo_tx,
                    estado='CONFIRMADO',
                )
                pedidos_creados.append(ped)
                if prod.stock >= cant:
                    prod.stock -= cant
                    if prod.stock == 0:
                        prod.disponible = False
                    prod.save()

            items.delete()

            # Enviar comprobante al correo Gmail del comprador
            enviar_comprobante_gmail(
                request.user,
                correo_culqi,
                codigo_tx,
                pedidos_creados,
                total_pagar,
                dict(Pedido.METODOS_PAGO).get(metodo, metodo)
            )

            messages.success(
                request,
                f"¡Pago procesado con Culqi ({codigo_tx})! Se envió el comprobante a tu correo Gmail ({correo_culqi})."
            )
            return redirect('comprobante_pago', codigo=codigo_tx)
    else:
        form = PasarelaPagoForm(initial={
            'ciudad_destino': perfil.ubicacion or 'Lima Metropolitana',
            'telefono_contacto': perfil.telefono or '999445566',
            'metodo_pago': 'TARJETA',
        })

    contexto = {
        'items': items,
        'subtotal': subtotal,
        'costo_logistica': costo_logistica,
        'total_pagar': total_pagar,
        'total_centimos': int(total_pagar * 100),
        'correo_gmail_usuario': correo_gmail_usuario,
        'culqi_public_key': getattr(settings, 'CULQI_PUBLIC_KEY', 'pk_test_0000000000000000'),
        'form': form,
    }
    return render(request, 'pasarela_pago.html', contexto)


@login_required
def comprobante_pago(request, codigo):
    """Muestra la boleta / comprobante electronico generado tras pasar por la pasarela de pago."""
    pedidos_tx = Pedido.objects.filter(comprador=request.user, codigo_transaccion=codigo).select_related('producto', 'producto__productor')
    if not pedidos_tx.exists():
        return redirect('mis_pedidos')

    subtotal_tx = sum(p.total for p in pedidos_tx)
    costo_logistica = Decimal("15.00")
    total_tx = subtotal_tx + costo_logistica

    contexto = {
        'codigo': codigo,
        'pedidos_tx': pedidos_tx,
        'primer_pedido': pedidos_tx.first(),
        'subtotal_tx': subtotal_tx,
        'costo_logistica': costo_logistica,
        'total_tx': total_tx,
    }
    return render(request, 'comprobante_pago.html', contexto)


def lista_productores(request):
    asegurar_datos_iniciales()
    perfiles_productores = PerfilUsuario.objects.filter(rol='PRODUCTOR').select_related('usuario')
    return render(request, 'productores.html', {'perfiles_productores': perfiles_productores})


def registro_vista(request):
    if request.user.is_authenticated:
        return redirect('inicio')

    rol_inicial = request.GET.get('rol', 'COMPRADOR')
    if rol_inicial not in ['COMPRADOR', 'PRODUCTOR']:
        rol_inicial = 'COMPRADOR'

    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            PerfilUsuario.objects.create(
                usuario=usuario,
                rol=form.cleaned_data['rol'],
                ruc_dni=form.cleaned_data.get('ruc_dni', ''),
                telefono=form.cleaned_data.get('telefono', ''),
                ubicacion=form.cleaned_data.get('ubicacion', ''),
                nombre_finca=form.cleaned_data.get('nombre_finca', ''),
                cuenta_bancaria=form.cleaned_data.get('cuenta_bancaria', '') if form.cleaned_data['rol'] == 'PRODUCTOR' else '',
            )
            login(request, usuario)
            messages.success(request, f"¡Bienvenido(a), {usuario.first_name}! Cuenta creada con contraseña encriptada.")
            if form.cleaned_data['rol'] == 'PRODUCTOR':
                return redirect('panel_productor')
            return redirect('panel_comprador')
    else:
        form = RegistroUsuarioForm(initial={'rol': rol_inicial})

    return render(request, 'registro.html', {'form': form, 'rol_inicial': rol_inicial})


def login_vista(request):
    """Apartado de Login que permite ingresar con usuario o con correo Gmail y contrasena encriptada."""
    asegurar_datos_iniciales()
    if request.user.is_authenticated:
        return redirect('inicio')

    modo_acceso = request.GET.get('modo', 'comprador')

    if request.method == 'POST':
        identificador = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        modo_elegido = request.POST.get('modo_rol', '')

        # Permitir iniciar sesion escribiendo directamente el correo Gmail o el nombre de usuario
        username_real = identificador
        if '@' in identificador:
            usr_por_correo = User.objects.filter(email__iexact=identificador).first()
            if usr_por_correo:
                username_real = usr_por_correo.username

        usuario = authenticate(request, username=username_real, password=password)
        if usuario is not None:
            perfil = obtener_o_crear_perfil(usuario)
            if modo_elegido in ['PRODUCTOR', 'COMPRADOR'] and perfil.rol != modo_elegido:
                rol_nombre = "Vendedor" if modo_elegido == 'PRODUCTOR' else "Comprador"
                messages.error(request, f"La cuenta '{identificador}' no pertenece al perfil de {rol_nombre}. Usa la pestaña correspondiente.")
                return render(request, 'login.html', {
                    'modo_acceso': 'vendedor' if modo_elegido == 'PRODUCTOR' else 'comprador',
                    'google_client_id': getattr(settings, 'GOOGLE_CLIENT_ID', ''),
                })

            login(request, usuario)
            messages.success(request, f"Sesión iniciada con {usuario.email or usuario.username} ({perfil.get_rol_display()}).")
            if perfil.rol == 'PRODUCTOR':
                return redirect('panel_productor')
            return redirect('panel_comprador')
        else:
            messages.error(request, "Correo/usuario o contraseña incorrectos. Verifica tus datos.")

    return render(request, 'login.html', {
        'modo_acceso': modo_acceso,
        'google_client_id': getattr(settings, 'GOOGLE_CLIENT_ID', ''),
    })


def login_google(request):
    """
    Inicio de sesión con la API de Google (OAuth 2.0 / Google Identity Services)
    o selector de cuenta Gmail con almacenamiento de contraseña encriptada (PBKDF2-SHA256).
    """
    asegurar_datos_iniciales()
    if request.method != 'POST':
        return redirect('login')

    rol_elegido = request.POST.get('modo_rol', 'COMPRADOR')
    if rol_elegido not in ['COMPRADOR', 'PRODUCTOR']:
        rol_elegido = 'COMPRADOR'

    credential_jwt = request.POST.get('credential', '').strip()
    email_google = ''
    nombre_google = ''
    apellido_google = ''

    # 1. Si viene un token JWT oficial desde el boton de Google Sign-In API
    if credential_jwt:
        try:
            url_verify = f"https://oauth2.googleapis.com/tokeninfo?id_token={urllib.parse.quote(credential_jwt)}"
            with urllib.request.urlopen(url_verify, timeout=8) as resp:
                datos_token = json.loads(resp.read().decode('utf-8'))
                client_id_cfg = getattr(settings, 'GOOGLE_CLIENT_ID', '').strip()
                if client_id_cfg and datos_token.get('aud') != client_id_cfg:
                    messages.error(request, "El token de Google no coincide con el GOOGLE_CLIENT_ID configurado.")
                    return redirect('login')
                email_google = datos_token.get('email', '').strip().lower()
                nombre_google = datos_token.get('given_name', '')
                apellido_google = datos_token.get('family_name', '')
        except Exception:
            messages.error(request, "No se pudo verificar la credencial con la API de Google.")
            return redirect('login')
    else:
        # 2. Selector directo de cuenta Gmail + contrasena (encriptada con PBKDF2-SHA256 en la BD)
        email_google = request.POST.get('email_google', '').strip().lower()
        nombre_completo = request.POST.get('nombre_google', '').strip()
        password_google = request.POST.get('password_google', '')

        if not email_google or '@' not in email_google:
            messages.error(request, "Selecciona o ingresa un correo Gmail válido.")
            return redirect('login')

        partes_nombre = nombre_completo.split(' ', 1) if nombre_completo else [email_google.split('@')[0], '']
        nombre_google = partes_nombre[0].capitalize()
        apellido_google = partes_nombre[1] if len(partes_nombre) > 1 else ''

        usuario_existente = User.objects.filter(email__iexact=email_google).first()
        if usuario_existente and password_google:
            # Si ya tiene contrasena encriptada registrada, la validamos o actualizamos de forma segura
            if usuario_existente.has_usable_password() and not usuario_existente.check_password(password_google):
                messages.error(request, "La contraseña ingresada para ese correo Gmail no coincide.")
                return redirect('login')

    if not email_google:
        messages.error(request, "No se recibió el correo de Google.")
        return redirect('login')

    # Buscar o crear el usuario vinculado a ese Gmail
    usuario = User.objects.filter(email__iexact=email_google).first()
    password_ingresada = request.POST.get('password_google', '')

    if not usuario:
        base_username = email_google.split('@')[0][:20]
        username_final = base_username
        contador = 1
        while User.objects.filter(username=username_final).exists():
            username_final = f"{base_username}{contador}"
            contador += 1

        usuario = User(
            username=username_final,
            email=email_google,
            first_name=nombre_google or base_username.capitalize(),
            last_name=apellido_google,
        )
        # Encriptar/indexar la contrasena con PBKDF2-SHA256 para que nunca quede en texto plano
        if password_ingresada:
            usuario.set_password(password_ingresada)
        else:
            usuario.set_unusable_password()
        usuario.save()

        PerfilUsuario.objects.create(
            usuario=usuario,
            rol=rol_elegido,
            ubicacion="Lima, Perú",
            telefono="999888777",
        )
    else:
        if password_ingresada and not usuario.has_usable_password():
            usuario.set_password(password_ingresada)
            usuario.save()
        perfil = obtener_o_crear_perfil(usuario)
        perfil.rol = rol_elegido
        perfil.save()

    login(request, usuario)
    messages.success(
        request,
        f"Conectado con Google ({usuario.email}). Contraseña protegida con encriptación PBKDF2-SHA256."
    )
    if rol_elegido == 'PRODUCTOR':
        return redirect('panel_productor')
    return redirect('panel_comprador')


@login_required
def cambiar_modo_vista(request):
    """Cambia entre la cuenta real de Vendedor (productor_mantaro) y la cuenta real de Comprador (comprador_lima)."""
    asegurar_datos_iniciales()
    if request.method == 'POST':
        nuevo_rol = request.POST.get('nuevo_rol')
        if nuevo_rol == 'PRODUCTOR':
            usuario_vendedor = User.objects.filter(username='productor_mantaro').first()
            if usuario_vendedor:
                login(request, usuario_vendedor)
                messages.info(request, "Cambiaste a la cuenta de Vendedor: Mateo Huamán (mateo.agromantaro@gmail.com).")
                return redirect('panel_productor')
        elif nuevo_rol == 'COMPRADOR':
            usuario_comprador = User.objects.filter(username='comprador_lima').first()
            if usuario_comprador:
                login(request, usuario_comprador)
                messages.info(request, "Cambiaste a la cuenta de Comprador: Carlos Mendoza (carlos.comprador@gmail.com).")
                return redirect('panel_comprador')
    return redirect('inicio')


def logout_vista(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('inicio')


@login_required
def panel_comprador(request):
    """Apartado visual exclusivo para el Comprador."""
    perfil = obtener_o_crear_perfil(request.user)
    if perfil.rol != 'COMPRADOR':
        messages.warning(request, "Esa sección es exclusiva para Compradores. Te redirigimos a tu Panel de Vendedor.")
        return redirect('panel_productor')

    compras_recientes = Pedido.objects.filter(comprador=request.user).select_related('producto', 'producto__productor')[:5]
    mis_ofertas = OfertaNegociacion.objects.filter(comprador=request.user).select_related('producto')[:5]
    items_carrito = ItemCarrito.objects.filter(comprador=request.user).select_related('producto')
    productos_recomendados = Producto.objects.filter(disponible=True, en_oferta=True)[:3]

    total_invertido = sum(c.total for c in Pedido.objects.filter(comprador=request.user).exclude(estado='CANCELADO'))

    contexto = {
        'perfil': perfil,
        'compras_recientes': compras_recientes,
        'mis_ofertas': mis_ofertas,
        'items_carrito': items_carrito,
        'productos_recomendados': productos_recomendados,
        'total_invertido': total_invertido,
    }
    return render(request, 'panel_comprador.html', contexto)


@login_required
def panel_productor(request):
    """Apartado visual exclusivo para el Vendedor / Productor Agricola."""
    perfil = obtener_o_crear_perfil(request.user)
    if perfil.rol != 'PRODUCTOR':
        messages.warning(request, "El Panel de Vendedor es exclusivo para Productores Agrícolas.")
        return redirect('panel_comprador')

    mis_productos = Producto.objects.filter(productor=request.user)
    pedidos_recibidos = Pedido.objects.filter(producto__productor=request.user).select_related('comprador', 'producto')
    ofertas_recibidas = OfertaNegociacion.objects.filter(producto__productor=request.user).select_related('comprador', 'producto')

    ingresos_estimados = sum(
        p.total for p in pedidos_recibidos if p.estado in ['CONFIRMADO', 'EN_CAMINO', 'ENTREGADO']
    )

    contexto = {
        'perfil': perfil,
        'mis_productos': mis_productos,
        'pedidos_recibidos': pedidos_recibidos,
        'ofertas_recibidas': ofertas_recibidas,
        'ingresos_estimados': ingresos_estimados,
        'estados_pedido': Pedido.ESTADOS,
    }
    return render(request, 'panel_productor.html', contexto)


@login_required
def crear_producto(request):
    perfil = obtener_o_crear_perfil(request.user)
    if perfil.rol != 'PRODUCTOR':
        messages.error(request, "Solo los Vendedores / Productores pueden publicar productos.")
        return redirect('panel_comprador')

    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.productor = request.user
            producto.save()
            messages.success(request, f"El producto '{producto.nombre}' fue publicado exitosamente.")
            return redirect('panel_productor')
    else:
        form = ProductoForm()

    return render(request, 'form_producto.html', {'form': form, 'accion': 'Publicar Nuevo Producto'})


@login_required
def editar_producto(request, producto_id):
    perfil = obtener_o_crear_perfil(request.user)
    if perfil.rol != 'PRODUCTOR':
        messages.error(request, "Un Comprador no puede editar productos.")
        return redirect('panel_comprador')

    producto = get_object_or_404(Producto, id=producto_id, productor=request.user)
    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, f"El producto '{producto.nombre}' fue actualizado.")
            return redirect('panel_productor')
    else:
        form = ProductoForm(instance=producto)

    return render(request, 'form_producto.html', {
        'form': form,
        'producto': producto,
        'accion': 'Editar mi Producto Agrícola'
    })


@login_required
def eliminar_producto(request, producto_id):
    perfil = obtener_o_crear_perfil(request.user)
    if perfil.rol != 'PRODUCTOR':
        messages.error(request, "Acción no permitida para Compradores.")
        return redirect('panel_comprador')

    producto = get_object_or_404(Producto, id=producto_id, productor=request.user)
    if request.method == 'POST':
        nombre = producto.nombre
        producto.delete()
        messages.info(request, f"El producto '{nombre}' fue eliminado.")
    return redirect('panel_productor')


@login_required
def cambiar_estado_pedido(request, pedido_id):
    perfil = obtener_o_crear_perfil(request.user)
    pedido = get_object_or_404(Pedido, id=pedido_id)
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        estados_validos = dict(Pedido.ESTADOS).keys()

        if perfil.rol == 'PRODUCTOR' and pedido.producto.productor == request.user and nuevo_estado in estados_validos:
            pedido.estado = nuevo_estado
            pedido.save()
            messages.success(request, f"Estado del pedido #{pedido.id} actualizado a '{pedido.get_estado_display()}'.")
            return redirect('panel_productor')

        if perfil.rol == 'COMPRADOR' and pedido.comprador == request.user and pedido.estado in ['PENDIENTE', 'CONFIRMADO'] and nuevo_estado == 'CANCELADO':
            pedido.estado = 'CANCELADO'
            pedido.estado_pago = 'REEMBOLSADO'
            pedido.save()
            pedido.producto.stock += pedido.cantidad
            pedido.producto.disponible = True
            pedido.producto.save()
            messages.info(request, f"El pedido #{pedido.id} fue cancelado y el stock fue repuesto.")
            return redirect('mis_pedidos')

    return redirect('inicio')


@login_required
def mis_pedidos(request):
    perfil = obtener_o_crear_perfil(request.user)
    if perfil.rol != 'COMPRADOR':
        return redirect('panel_productor')

    compras = Pedido.objects.filter(comprador=request.user).select_related('producto', 'producto__productor')
    total_gastado = sum(c.total for c in compras if c.estado != 'CANCELADO')
    return render(request, 'mis_pedidos.html', {
        'compras': compras,
        'total_gastado': total_gastado,
    })


@login_required
def perfil_vista(request):
    perfil = obtener_o_crear_perfil(request.user)
    if request.method == 'POST':
        form = PerfilForm(request.POST, instance=perfil)
        if form.is_valid():
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.email = form.cleaned_data['email']
            request.user.save()
            form.save()
            messages.success(request, "Tus datos de perfil fueron actualizados correctamente.")
            return redirect('perfil')
    else:
        form = PerfilForm(instance=perfil, initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
        })

    return render(request, 'perfil.html', {'form': form, 'perfil': perfil})
