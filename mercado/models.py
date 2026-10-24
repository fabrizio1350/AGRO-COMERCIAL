from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class PerfilUsuario(models.Model):
    ROLES = [
        ('PRODUCTOR', 'Vendedor / Productor Agrícola'),
        ('COMPRADOR', 'Comprador / Mayorista / Cliente'),
    ]

    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    rol = models.CharField(max_length=15, choices=ROLES, default='COMPRADOR')
    telefono = models.CharField(max_length=20, blank=True)
    ubicacion = models.CharField(max_length=120, blank=True)
    nombre_finca = models.CharField(max_length=120, blank=True, help_text="Finca, asociación o empresa comercial")
    ruc_dni = models.CharField(max_length=20, blank=True, help_text="DNI o RUC")
    cuenta_bancaria = models.CharField(max_length=120, blank=True, help_text="Número de cuenta en soles (solo vendedores)")

    def __str__(self):
        return f"{self.usuario.username} ({self.get_rol_display()})"


class Categoria(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Categorías"

    def url_imagen(self):
        nombre_low = self.nombre.lower()
        if 'tub' in nombre_low or 'papa' in nombre_low:
            return '/static/imagenes/papa_amarilla.jpg'
        if 'hortaliza' in nombre_low or 'verdura' in nombre_low:
            return '/static/imagenes/zanahoria.jpg'
        if 'fruta' in nombre_low:
            return '/static/imagenes/mandarina.jpg'
        if 'grano' in nombre_low or 'cereal' in nombre_low:
            return '/static/imagenes/quinua_blanca.jpg'
        return '/static/imagenes/finca_productor.jpg'

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    UNIDADES = [
        ('KG', 'Kilogramo (kg)'),
        ('SACO', 'Saco (50 kg)'),
        ('CAJA', 'Caja (20 kg)'),
        ('ARROBA', 'Arroba (11.5 kg)'),
        ('TONELADA', 'Tonelada (1000 kg)'),
    ]

    TIPOS_CULTIVO = [
        ('TRADICIONAL', 'Cultivo Tradicional de Campo'),
        ('ORGANICO', 'Orgánico Natural (Sin químicos)'),
        ('INVERNADERO', 'Huerto / Riego Tecnificado'),
    ]

    NIVELES_CALIDAD = [
        ('PRIMERA', 'Primera Calidad (Seleccionado / Grande)'),
        ('ESTANDAR', 'Calidad Estándar (Mediano / Comercial)'),
        ('ECONOMICA', 'Económico (Ideal para negocio o restaurante)'),
    ]

    productor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='productos')
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, related_name='productos')
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField()
    variedad = models.CharField(max_length=80, blank=True, default='Fresco de campo')
    tipo_cultivo = models.CharField(max_length=20, choices=TIPOS_CULTIVO, default='TRADICIONAL')
    fecha_cosecha = models.DateField(default=timezone.now)
    calidad = models.CharField(max_length=20, choices=NIVELES_CALIDAD, default='PRIMERA')
    precio = models.DecimalField(max_digits=8, decimal_places=2)
    en_oferta = models.BooleanField(default=False)
    precio_oferta = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    acepta_ofertas = models.BooleanField(default=True, help_text="Permite que compradores envíen contraofertas de precio")
    unidad = models.CharField(max_length=15, choices=UNIDADES, default='KG')
    stock = models.PositiveIntegerField(default=1)
    minimo_compra = models.PositiveIntegerField(default=1)
    origen = models.CharField(max_length=120, help_text="Región o valle de cosecha")
    imagen_url = models.CharField(max_length=350, blank=True, help_text="Enlace de imagen de referencia (opcional)")
    disponible = models.BooleanField(default=True)
    fecha_publicacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_publicacion']

    def precio_actual(self):
        if self.en_oferta and self.precio_oferta and self.precio_oferta < self.precio:
            return self.precio_oferta
        return self.precio

    def porcentaje_descuento(self):
        if self.en_oferta and self.precio_oferta and self.precio > 0 and self.precio_oferta < self.precio:
            descuento = ((self.precio - self.precio_oferta) / self.precio) * 100
            return int(round(descuento))
        return 0

    def url_imagen(self):
        if self.imagen_url and self.imagen_url.strip():
            return self.imagen_url.strip()
        texto = f"{self.nombre} {self.variedad}".lower()
        if 'papa' in texto or 'camote' in texto or 'yuca' in texto:
            return '/static/imagenes/papa_amarilla.jpg'
        if 'quinua' in texto or 'maíz' in texto or 'maiz' in texto or 'grano' in texto:
            return '/static/imagenes/quinua_blanca.jpg'
        if 'zanahoria' in texto:
            return '/static/imagenes/zanahoria.jpg'
        if 'mandarina' in texto or 'naranja' in texto:
            return '/static/imagenes/mandarina.jpg'
        if 'palta' in texto:
            return '/static/imagenes/palta_hass.jpg'
        if 'tomate' in texto:
            return '/static/imagenes/tomate.jpg'
        if self.categoria:
            return self.categoria.url_imagen()
        return '/static/imagenes/finca_productor.jpg'

    def __str__(self):
        return f"{self.nombre} - S/ {self.precio_actual()} ({self.get_unidad_display()})"


class OfertaNegociacion(models.Model):
    """Permite a los compradores proponer un precio por volumen/lote al vendedor."""
    ESTADOS_OFERTA = [
        ('PENDIENTE', 'Pendiente'),
        ('ACEPTADA', 'Aceptada'),
        ('RECHAZADA', 'Rechazada'),
        ('PAGADA', 'Comprada'),
    ]

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='ofertas_recibidas')
    comprador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ofertas_enviadas')
    cantidad = models.PositiveIntegerField(default=10)
    precio_unitario_ofrecido = models.DecimalField(max_digits=8, decimal_places=2)
    mensaje = models.CharField(max_length=250, blank=True)
    respuesta_vendedor = models.CharField(max_length=250, blank=True)
    estado = models.CharField(max_length=15, choices=ESTADOS_OFERTA, default='PENDIENTE')
    fecha_oferta = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_oferta']

    def total_ofrecido(self):
        return self.cantidad * self.precio_unitario_ofrecido

    def __str__(self):
        return f"Oferta #{self.id} de {self.comprador.username} por {self.producto.nombre}"


class ItemCarrito(models.Model):
    comprador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='items_carrito')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario_acordado = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    fecha_agregado = models.DateTimeField(auto_now_add=True)

    def precio_aplicado(self):
        if self.precio_unitario_acordado:
            return self.precio_unitario_acordado
        return self.producto.precio_actual()

    def subtotal(self):
        return self.cantidad * self.precio_aplicado()


class Pedido(models.Model):
    ESTADOS = [
        ('PENDIENTE', 'Pendiente de confirmación'),
        ('CONFIRMADO', 'Confirmado y en preparación'),
        ('EN_CAMINO', 'En transporte hacia destino'),
        ('ENTREGADO', 'Entregado al comprador'),
        ('CANCELADO', 'Cancelado'),
    ]

    METODOS_PAGO = [
        ('TARJETA', 'Tarjeta de Crédito / Débito (Visa / Mastercard)'),
        ('YAPE_PLIN', 'Billetera Digital (Yape / Plin QR)'),
        ('TRANSFERENCIA', 'Transferencia Bancaria Agro / Interbancaria'),
        ('CONTRAENTREGA', 'Pago Contraentrega en Almacén'),
    ]

    ESTADOS_PAGO = [
        ('PAGADO', 'Pago Verificado en Pasarela'),
        ('PENDIENTE_VERIFICACION', 'Pendiente de Verificación'),
        ('REEMBOLSADO', 'Reembolsado'),
    ]

    comprador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='compras')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='pedidos')
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    direccion_entrega = models.CharField(max_length=200)
    ciudad_destino = models.CharField(max_length=100, default='Lima')
    telefono_contacto = models.CharField(max_length=30, blank=True)
    comentario = models.TextField(blank=True)
    metodo_pago = models.CharField(max_length=20, choices=METODOS_PAGO, default='TARJETA')
    estado_pago = models.CharField(max_length=25, choices=ESTADOS_PAGO, default='PAGADO')
    codigo_transaccion = models.CharField(max_length=40, blank=True)
    estado = models.CharField(max_length=15, choices=ESTADOS, default='CONFIRMADO')
    fecha_pedido = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_pedido']

    def __str__(self):
        return f"Pedido #{self.id} - {self.producto.nombre} ({self.comprador.username})"


class ResenaProducto(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='resenas')
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    calificacion = models.PositiveSmallIntegerField(default=5)
    comentario = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']
