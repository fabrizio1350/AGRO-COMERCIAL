from decimal import Decimal
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# Por ahora la plataforma solo trabaja en Arequipa: estos son los lugares de compra y venta
LUGARES_AREQUIPA = [
    'Arequipa (Cercado), Arequipa',
    'Cayma, Arequipa',
    'Cerro Colorado, Arequipa',
    'Yanahuara, Arequipa',
    'Paucarpata, Arequipa',
    'José Luis Bustamante y Rivero, Arequipa',
    'Socabaya, Arequipa',
    'Sachaca, Arequipa',
    'Tiabaya, Arequipa',
    'Characato, Arequipa',
    'Sabandía, Arequipa',
    'Chiguata, Arequipa',
    'Mollebaya, Arequipa',
    'Uchumayo, Arequipa',
    'Yura, Arequipa',
    'La Joya, Arequipa',
    'Majes (Caylloma), Arequipa',
    'Chivay (Caylloma), Arequipa',
    'Valle de Tambo (Islay), Arequipa',
    'Mollendo (Islay), Arequipa',
    'Camaná, Arequipa',
    'Aplao (Castilla), Arequipa',
    'Chuquibamba (Condesuyos), Arequipa',
    'Cotahuasi (La Unión), Arequipa',
    'Caravelí, Arequipa',
]
LUGAR_POR_DEFECTO = 'Arequipa (Cercado), Arequipa'
OPCIONES_LUGARES = [(lugar, lugar.replace(', Arequipa', '')) for lugar in LUGARES_AREQUIPA]

# Categorias que puede elegir el vendedor al publicar (nombre, descripcion)
CATEGORIAS_AGRICOLAS = [
    ("Tubérculos y Raíces", "Papas nativas, camotes, yucas y ollucos cosechados en sierra y costa."),
    ("Hortalizas y Verduras", "Verduras frescas de huerta listas para distribución directa."),
    ("Frutas de Estación", "Frutas seleccionadas directamente de los valles productores."),
    ("Granos y Cereales", "Quinua, maíz amiláceo, habas secas y menestras andinas."),
    ("Legumbres y Menestras", "Frijol, haba, arveja, pallar y lenteja secos o en vaina."),
    ("Ajíes, Rocotos y Condimentos", "Rocoto arequipeño, ají amarillo, panca, ajo y cebolla."),
    ("Hierbas Aromáticas y Medicinales", "Huacatay, muña, orégano, hierba buena y plantas medicinales."),
    ("Lácteos y Quesos", "Leche fresca, queso paria, queso fresco y derivados del campo."),
    ("Forrajes y Pastos", "Alfalfa, avena forrajera y pastos para ganado."),
    ("Semillas y Plantones", "Semillas certificadas y plantones para siembra."),
    ("Frutos Secos y Deshidratados", "Pasas, higos secos, nueces y frutas deshidratadas."),
    ("Flores y Plantas Ornamentales", "Flores de corte y plantas de vivero."),
    ("Huevos y Animales Menores", "Huevos de granja, cuyes y aves de corral."),
]


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
        # Para las categorias nuevas se usa la foto que subio algun vendedor
        con_foto = self.productos.exclude(imagen='').exclude(imagen__isnull=True).first()
        if con_foto:
            return con_foto.imagen.url
        return '/static/imagenes/banner_agro.jpg'

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
    imagen = models.FileField(
        upload_to='productos/',
        blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
        help_text="Foto del producto subida por el vendedor",
    )
    imagen_url = models.CharField(max_length=350, blank=True, help_text="Enlace de imagen de referencia (opcional)")
    disponible = models.BooleanField(default=True)
    oferta_pendiente_pago = models.BooleanField(default=False, help_text="La oferta no se publica hasta pagar la comisión")
    fecha_publicacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_publicacion']

    def precio_actual(self):
        if self.en_oferta and self.precio_oferta and self.precio_oferta < self.precio:
            return self.precio_oferta
        return self.precio

    def valor_oferta(self):
        """Valor total del lote en oferta (precio de oferta x stock)."""
        if self.precio_oferta:
            return self.precio_oferta * self.stock
        return Decimal('0.00')

    def monto_comision_oferta(self):
        """Comisión que cobra AgroComercial por publicar el producto como oferta."""
        porcentaje = Decimal(str(settings.COMISION_OFERTA_PORCENTAJE))
        minimo = Decimal(str(settings.COMISION_OFERTA_MINIMA))
        monto = (self.valor_oferta() * porcentaje / 100).quantize(Decimal('0.01'))
        return max(monto, minimo)

    def porcentaje_descuento(self):
        if self.en_oferta and self.precio_oferta and self.precio > 0 and self.precio_oferta < self.precio:
            descuento = ((self.precio - self.precio_oferta) / self.precio) * 100
            return int(round(descuento))
        return 0

    def nombre_unidad_stock(self):
        """Devuelve la unidad en formato corto y claro según la cantidad en stock (ej. 'kg', 'cajas', 'sacos', 'toneladas')."""
        unidades_cortas = {
            'KG': ('kg', 'kg'),
            'SACO': ('saco', 'sacos'),
            'CAJA': ('caja', 'cajas'),
            'ARROBA': ('arroba', 'arrobas'),
            'TONELADA': ('tonelada', 'toneladas'),
        }
        singular, plural = unidades_cortas.get(self.unidad, ('unidad', 'unidades'))
        return singular if self.stock == 1 else plural

    def nombre_unidad_minimo(self):
        """Devuelve la unidad según la cantidad mínima de compra."""
        unidades_cortas = {
            'KG': ('kg', 'kg'),
            'SACO': ('saco', 'sacos'),
            'CAJA': ('caja', 'cajas'),
            'ARROBA': ('arroba', 'arrobas'),
            'TONELADA': ('tonelada', 'toneladas'),
        }
        singular, plural = unidades_cortas.get(self.unidad, ('unidad', 'unidades'))
        return singular if self.minimo_compra == 1 else plural

    def url_imagen(self):
        if self.imagen:
            return self.imagen.url
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
    ciudad_destino = models.CharField(max_length=100, default=LUGAR_POR_DEFECTO)
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


class PagoComision(models.Model):
    """Registro del pago (simulado) de la comisión por publicar un producto en oferta."""
    METODOS = [
        ('YAPE_PLIN', 'Yape / Plin'),
        ('TARJETA', 'Tarjeta de Crédito / Débito'),
    ]

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='pagos_comision')
    productor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pagos_comision')
    porcentaje = models.DecimalField(max_digits=5, decimal_places=2)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = models.CharField(max_length=20, choices=METODOS, default='YAPE_PLIN')
    codigo_transaccion = models.CharField(max_length=40)
    fecha_pago = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_pago']

    def __str__(self):
        return f"Comisión {self.codigo_transaccion} - {self.producto.nombre} (S/ {self.monto})"


class ResenaProducto(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='resenas')
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    calificacion = models.PositiveSmallIntegerField(default=5)
    comentario = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']
