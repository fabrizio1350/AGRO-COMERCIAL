from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from .models import PerfilUsuario, Categoria, Producto, Pedido
from .forms import RegistroUsuarioForm, ProductoForm, PedidoForm, PerfilForm


def asegurar_datos_iniciales():
    """Crea datos de prueba iniciales si la base de datos esta vacia."""
    if Categoria.objects.exists():
        return

    cat_tuberculos = Categoria.objects.create(
        nombre="Tubérculos y Raíces",
        descripcion="Papas nativas, camotes, yucas y ollucos cosechados en sierra y costa."
    )
    cat_hortalizas = Categoria.objects.create(
        nombre="Hortalizas y Verduras",
        descripcion="Verduras frescas de huerta listas para distribución directa."
    )
    cat_frutas = Categoria.objects.create(
        nombre="Frutas de Estación",
        descripcion="Frutas seleccionadas directamente de los valles productores."
    )
    cat_granos = Categoria.objects.create(
        nombre="Granos y Cereales",
        descripcion="Quinua, maíz amiláceo, habas secas y menestras andinas."
    )

    productor1, creado1 = User.objects.get_or_create(
        username="productor_mantaro",
        defaults={
            "first_name": "Mateo",
            "last_name": "Huamán",
            "email": "mateo@agromantaro.pe",
        }
    )
    if creado1:
        productor1.set_password("agro12345")
        productor1.save()
        PerfilUsuario.objects.create(
            usuario=productor1,
            rol="PRODUCTOR",
            telefono="964112233",
            ubicacion="Huancayo, Junín",
            nombre_finca="Asociación Agrícola Valle del Mantaro"
        )

    productor2, creado2 = User.objects.get_or_create(
        username="productor_huaral",
        defaults={
            "first_name": "Elena",
            "last_name": "Rojas",
            "email": "elena@fundoelena.pe",
        }
    )
    if creado2:
        productor2.set_password("agro12345")
        productor2.save()
        PerfilUsuario.objects.create(
            usuario=productor2,
            rol="PRODUCTOR",
            telefono="945887766",
            ubicacion="Huaral, Lima",
            nombre_finca="Fundo Santa Elena"
        )

    comprador_demo, creado3 = User.objects.get_or_create(
        username="comprador_lima",
        defaults={
            "first_name": "Carlos",
            "last_name": "Mendoza",
            "email": "carlos@comercialmendoza.pe",
        }
    )
    if creado3:
        comprador_demo.set_password("agro12345")
        comprador_demo.save()
        PerfilUsuario.objects.create(
            usuario=comprador_demo,
            rol="COMPRADOR",
            telefono="999445566",
            ubicacion="Lima Metropolitana",
            nombre_finca=""
        )

    productos_demo = [
        {
            "productor": productor1,
            "categoria": cat_tuberculos,
            "nombre": "Papa Amarilla Tumbay Seleccionada",
            "descripcion": "Papa amarilla de primera calidad, cosecha reciente libre de químicos agresivos. Ideal para mercados minoristas y restaurantes.",
            "precio": Decimal("3.80"),
            "unidad": "KG",
            "stock": 450,
            "origen": "Huancayo, Junín",
        },
        {
            "productor": productor1,
            "categoria": cat_granos,
            "nombre": "Quinua Blanca Orgánica",
            "descripcion": "Grano seleccionado, limpio y secado de forma natural en altura. Alto valor nutritivo.",
            "precio": Decimal("9.50"),
            "unidad": "KG",
            "stock": 200,
            "origen": "Jauja, Junín",
        },
        {
            "productor": productor1,
            "categoria": cat_hortalizas,
            "nombre": "Zanahoria Fresca de Sierra (Saco)",
            "descripcion": "Saco de 50 kg de zanahoria fresca recién lavada y clasificada por tamaño mediano-grande.",
            "precio": Decimal("65.00"),
            "unidad": "SACO",
            "stock": 35,
            "origen": "Tarma, Junín",
        },
        {
            "productor": productor2,
            "categoria": cat_frutas,
            "nombre": "Mandarina Satsuma sin Pepa",
            "descripcion": "Caja de 20 kg de mandarina dulce de exportación, cosechada esta semana en el valle de Huaral.",
            "precio": Decimal("48.00"),
            "unidad": "CAJA",
            "stock": 60,
            "origen": "Huaral, Lima",
        },
        {
            "productor": productor2,
            "categoria": cat_frutas,
            "nombre": "Palta Hass de Exportación",
            "descripcion": "Palta Hass con materia seca óptima, piel rugosa y excelente conservación para transporte.",
            "precio": Decimal("6.20"),
            "unidad": "KG",
            "stock": 300,
            "origen": "Chancay, Lima",
        },
        {
            "productor": productor2,
            "categoria": cat_hortalizas,
            "nombre": "Tomate Río Grande Seleccionado",
            "descripcion": "Caja de 20 kg de tomate firme, maduración uniforme para distribución directa.",
            "precio": Decimal("42.00"),
            "unidad": "CAJA",
            "stock": 40,
            "origen": "Barranca, Lima",
        },
    ]

    for datos in productos_demo:
        Producto.objects.create(**datos)


def obtener_o_crear_perfil(usuario):
    perfil, _ = PerfilUsuario.objects.get_or_create(usuario=usuario)
    return perfil


def inicio(request):
    asegurar_datos_iniciales()
    categorias = Categoria.objects.all()
    productos_destacados = Producto.objects.filter(disponible=True, stock__gt=0)[:6]
    total_productos = Producto.objects.filter(disponible=True).count()
    total_productores = PerfilUsuario.objects.filter(rol='PRODUCTOR').count()
    total_pedidos = Pedido.objects.count()

    contexto = {
        'categorias': categorias,
        'productos_destacados': productos_destacados,
        'total_productos': total_productos,
        'total_productores': total_productores,
        'total_pedidos': total_pedidos,
    }
    return render(request, 'inicio.html', contexto)


def catalogo(request):
    asegurar_datos_iniciales()
    productos = Producto.objects.filter(disponible=True)
    categorias = Categoria.objects.all()

    busqueda = request.GET.get('q', '').strip()
    categoria_id = request.GET.get('categoria', '').strip()
    productor_id = request.GET.get('productor', '').strip()
    unidad = request.GET.get('unidad', '').strip()

    if busqueda:
        productos = productos.filter(
            Q(nombre__icontains=busqueda) |
            Q(descripcion__icontains=busqueda) |
            Q(origen__icontains=busqueda)
        )
    if categoria_id.isdigit():
        productos = productos.filter(categoria_id=int(categoria_id))
    if productor_id.isdigit():
        productos = productos.filter(productor_id=int(productor_id))
    if unidad:
        productos = productos.filter(unidad=unidad)

    contexto = {
        'productos': productos,
        'categorias': categorias,
        'unidades': Producto.UNIDADES,
        'busqueda': busqueda,
        'categoria_seleccionada': categoria_id,
        'productor_seleccionado': productor_id,
        'unidad_seleccionada': unidad,
    }
    return render(request, 'catalogo.html', contexto)


def detalle_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    relacionados = Producto.objects.filter(
        categoria=producto.categoria,
        disponible=True
    ).exclude(id=producto.id)[:3]

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.warning(request, "Debes iniciar sesión para realizar un pedido.")
            return redirect('login')

        form = PedidoForm(request.POST)
        if form.is_valid():
            cantidad = form.cleaned_data['cantidad']
            if cantidad > producto.stock:
                messages.error(request, f"Solo quedan {producto.stock} unidades disponibles en stock.")
            elif producto.productor == request.user:
                messages.warning(request, "No puedes realizar un pedido de tu propio producto.")
            else:
                pedido = form.save(commit=False)
                pedido.comprador = request.user
                pedido.producto = producto
                pedido.total = producto.precio * cantidad
                pedido.save()

                producto.stock -= cantidad
                if producto.stock == 0:
                    producto.disponible = False
                producto.save()

                messages.success(request, f"¡Pedido #{pedido.id} registrado con éxito! Total: S/ {pedido.total}")
                return redirect('mis_pedidos')
    else:
        form = PedidoForm()

    contexto = {
        'producto': producto,
        'relacionados': relacionados,
        'form': form,
    }
    return render(request, 'detalle_producto.html', contexto)


def lista_productores(request):
    asegurar_datos_iniciales()
    perfiles_productores = PerfilUsuario.objects.filter(rol='PRODUCTOR').select_related('usuario')
    return render(request, 'productores.html', {'perfiles_productores': perfiles_productores})


def registro_vista(request):
    if request.user.is_authenticated:
        return redirect('inicio')

    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            PerfilUsuario.objects.create(
                usuario=usuario,
                rol=form.cleaned_data['rol'],
                telefono=form.cleaned_data['telefono'],
                ubicacion=form.cleaned_data['ubicacion'],
                nombre_finca=form.cleaned_data['nombre_finca'],
            )
            login(request, usuario)
            messages.success(request, f"¡Bienvenido(a), {usuario.first_name}! Tu cuenta ha sido creada.")
            if form.cleaned_data['rol'] == 'PRODUCTOR':
                return redirect('panel_productor')
            return redirect('catalogo')
    else:
        form = RegistroUsuarioForm()

    return render(request, 'registro.html', {'form': form})


def login_vista(request):
    asegurar_datos_iniciales()
    if request.user.is_authenticated:
        return redirect('inicio')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        usuario = authenticate(request, username=username, password=password)
        if usuario is not None:
            login(request, usuario)
            perfil = obtener_o_crear_perfil(usuario)
            messages.success(request, f"Sesión iniciada como {usuario.username} ({perfil.get_rol_display()}).")
            if perfil.rol == 'PRODUCTOR':
                return redirect('panel_productor')
            return redirect('catalogo')
        else:
            messages.error(request, "Usuario o contraseña incorrectos. Intenta nuevamente.")

    return render(request, 'login.html')


def logout_vista(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('inicio')


@login_required
def panel_productor(request):
    perfil = obtener_o_crear_perfil(request.user)
    mis_productos = Producto.objects.filter(productor=request.user)
    pedidos_recibidos = Pedido.objects.filter(producto__productor=request.user).select_related('comprador', 'producto')

    ingresos_estimados = sum(
        p.total for p in pedidos_recibidos if p.estado in ['CONFIRMADO', 'EN_CAMINO', 'ENTREGADO']
    )

    contexto = {
        'perfil': perfil,
        'mis_productos': mis_productos,
        'pedidos_recibidos': pedidos_recibidos,
        'ingresos_estimados': ingresos_estimados,
        'estados_pedido': Pedido.ESTADOS,
    }
    return render(request, 'panel_productor.html', contexto)


@login_required
def crear_producto(request):
    obtener_o_crear_perfil(request.user)
    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.productor = request.user
            producto.save()
            messages.success(request, f"El producto '{producto.nombre}' fue publicado en el catálogo.")
            return redirect('panel_productor')
    else:
        form = ProductoForm()

    return render(request, 'form_producto.html', {'form': form, 'accion': 'Publicar Nuevo Producto'})


@login_required
def editar_producto(request, producto_id):
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
        'accion': 'Editar Producto Agrícola'
    })


@login_required
def eliminar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id, productor=request.user)
    if request.method == 'POST':
        nombre = producto.nombre
        producto.delete()
        messages.info(request, f"El producto '{nombre}' fue eliminado.")
    return redirect('panel_productor')


@login_required
def cambiar_estado_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        estados_validos = dict(Pedido.ESTADOS).keys()

        # Si es el productor dueno del producto
        if pedido.producto.productor == request.user and nuevo_estado in estados_validos:
            pedido.estado = nuevo_estado
            pedido.save()
            messages.success(request, f"Estado del pedido #{pedido.id} actualizado a '{pedido.get_estado_display()}'.")
            return redirect('panel_productor')

        # Si es el comprador cancelando su pedido pendiente
        if pedido.comprador == request.user and pedido.estado == 'PENDIENTE' and nuevo_estado == 'CANCELADO':
            pedido.estado = 'CANCELADO'
            pedido.save()
            # Devolver el stock al producto
            pedido.producto.stock += pedido.cantidad
            pedido.producto.disponible = True
            pedido.producto.save()
            messages.info(request, f"El pedido #{pedido.id} fue cancelado y el stock fue repuesto.")
            return redirect('mis_pedidos')

    return redirect('inicio')


@login_required
def mis_pedidos(request):
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
