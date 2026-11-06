from decimal import Decimal
from urllib.parse import urlencode
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from datetime import timedelta
from django.db import models
from django.db.models import F, Q
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
        ('PRODUCTOR', 'Vendedor'),
        ('COMPRADOR', 'Comprador'),
    ]

    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    google_sub = models.CharField(max_length=255, null=True, blank=True, unique=True, editable=False)
    rol = models.CharField(max_length=15, choices=ROLES, default='COMPRADOR')
    telefono = models.CharField(max_length=20, blank=True)
    ubicacion = models.CharField(max_length=120, blank=True)
    nombre_finca = models.CharField(max_length=120, blank=True, help_text="Finca, asociación o empresa comercial")
    ruc_dni = models.CharField(max_length=20, blank=True, help_text="DNI o RUC")
    cuenta_bancaria = models.CharField(max_length=120, blank=True, help_text="Número de cuenta en soles (solo vendedores)")
    es_demo = models.BooleanField(default=False, help_text="Cuenta de prueba (bot): se muestra con la etiqueta Demo")
    ESTADOS_VERIFICACION = [
        ('SIN_ENVIAR', 'Sin enviar'),
        ('PENDIENTE', 'En revisión'),
        ('VERIFICADO', 'Verificado'),
        ('RECHAZADO', 'Rechazado'),
    ]
    estado_verificacion = models.CharField(max_length=12, choices=ESTADOS_VERIFICACION, default='SIN_ENVIAR')
    fecha_verificacion = models.DateTimeField(null=True, blank=True)
    organico_verificado = models.BooleanField(default=False, help_text="Tiene certificado orgánico revisado por el administrador")

    def vendedor_verificado(self):
        return self.estado_verificacion == 'VERIFICADO'

    def puede_vender_publicamente(self):
        # Las cuentas Demo se muestran (con su etiqueta) para la version de prueba
        return self.vendedor_verificado() or self.es_demo

    def __str__(self):
        return f"{self.usuario.username} ({self.get_rol_display()})"


class Puesto(models.Model):
    """Lugar fisico donde el vendedor atiende: se elige en el mapa y el comprador va hasta alli."""
    vendedor = models.OneToOneField(User, on_delete=models.CASCADE, related_name='puesto')
    nombre = models.CharField('Nombre del lugar', max_length=100)
    numero = models.CharField('N.º de puesto', max_length=20, blank=True)
    referencia = models.CharField('Referencia', max_length=150, blank=True)
    direccion = models.CharField('Dirección', max_length=200, blank=True)
    horario = models.CharField('Horario de atención', max_length=80, blank=True)
    foto = models.FileField('Foto del puesto', upload_to='puestos/', blank=True,
                            validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])])
    latitud = models.DecimalField(max_digits=8, decimal_places=6, validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitud = models.DecimalField(max_digits=9, decimal_places=6, validators=[MinValueValidator(-180), MaxValueValidator(180)])
    efectivo = models.BooleanField('Efectivo', default=True)
    tarjeta = models.BooleanField('Tarjeta (débito o crédito)', default=False)
    yape_plin = models.BooleanField('Yape / Plin', default=False)
    actualizado = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return f"{self.nombre} · {self.titulo_puesto()}"

    def titulo_puesto(self):
        return f"Puesto {self.numero}" if self.numero else "Puesto"

    def url_foto(self):
        if self.foto:
            return self.foto.url
        return '/static/imagenes/finca_productor.jpg'

    def como_llegar(self):
        return 'https://www.google.com/maps/dir/?' + urlencode({
            'api': 1, 'destination': f'{self.latitud},{self.longitud}',
        })

    def mapa_embebido(self):
        """Mapa de Google para mostrar el punto (no necesita llave de API)."""
        return 'https://maps.google.com/maps?' + urlencode({
            'q': f'{self.latitud},{self.longitud}', 'z': 17, 'output': 'embed', 'hl': 'es',
        })

    def metodos_pago(self):
        return [nombre for acepta, nombre in (
            (self.efectivo, 'Efectivo'), (self.tarjeta, 'Tarjeta'), (self.yape_plin, 'Yape / Plin'),
        ) if acepta]

    def iconos_pago(self):
        return [(icono, nombre) for acepta, icono, nombre in (
            (self.efectivo, 'bi-cash-coin', 'Efectivo'),
            (self.tarjeta, 'bi-credit-card', 'Tarjeta'),
            (self.yape_plin, 'bi-phone', 'Yape / Plin'),
        ) if acepta]


class Categoria(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Categorías"

    def foto_propia(self):
        """Foto real de la categoria (fija o subida por un vendedor); None si no tiene."""
        url = self.url_imagen()
        return None if url.endswith('banner_agro.jpg') else url

    def icono(self):
        """Icono de Bootstrap Icons para las categorias que aun no tienen foto."""
        nombre_low = self.nombre.lower()
        iconos = [
            ('aj', 'bi-fire'), ('flor', 'bi-flower2'), ('forraje', 'bi-tree'), ('seco', 'bi-sun'),
            ('hierba', 'bi-flower3'), ('huevo', 'bi-egg'), ('lácteo', 'bi-cup-straw'), ('lacteo', 'bi-cup-straw'),
            ('legumbre', 'bi-record-circle'), ('semilla', 'bi-grip-horizontal'),
        ]
        for clave, icono in iconos:
            if clave in nombre_low:
                return icono
        return 'bi-basket'

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


def fecha_vencimiento_por_defecto():
    """Cada publicacion dura PUBLICACION_DIAS_VIGENCIA dias si el vendedor no elige otra fecha."""
    return timezone.now() + timedelta(days=settings.PUBLICACION_DIAS_VIGENCIA)


class ProductoQuerySet(models.QuerySet):
    def publicados(self):
        """Productos que se ven en la web: activos, con stock, sin vencer y de un vendedor con su puesto en el mapa.
        Con VERIFICACION_OBLIGATORIA solo se muestran los puestos verificados (y los Demo)."""
        ahora = timezone.now()
        consulta = self.filter(disponible=True, stock__gt=0).filter(
            Q(fecha_vencimiento__isnull=True) | Q(fecha_vencimiento__gt=ahora)
        ).filter(
            productor__puesto__isnull=False, productor__perfil__rol='PRODUCTOR', productor__is_active=True,
        )
        if settings.VERIFICACION_OBLIGATORIA:
            consulta = consulta.filter(Q(productor__perfil__estado_verificacion='VERIFICADO') | Q(productor__perfil__es_demo=True))
        return consulta

    def ofertas_activas(self):
        """Ofertas pagadas, con precio menor al normal y dentro de sus fechas."""
        ahora = timezone.now()
        return self.publicados().filter(
            en_oferta=True,
            oferta_pendiente_pago=False,
            precio_oferta__isnull=False,
            precio_oferta__lt=F('precio'),
        ).filter(
            Q(oferta_inicio__isnull=True) | Q(oferta_inicio__lte=ahora)
        ).filter(
            Q(oferta_fin__isnull=True) | Q(oferta_fin__gt=ahora)
        )


class Producto(models.Model):
    UNIDADES = [
        ('UNIDAD', 'Unidad'),
        ('KG', 'Kilogramo (kg)'),
        ('DOCENA', 'Docena'),
        ('ATADO', 'Atado'),
        ('BOLSA', 'Bolsa'),
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
    stock_actualizado = models.DateTimeField(null=True, blank=True)
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
    ubicacion = models.ForeignKey(
        'UbicacionVendedor', on_delete=models.SET_NULL, null=True, blank=True, related_name='productos',
        help_text="Otra ubicación donde se vende; vacío = el puesto principal",
    )
    fecha_publicacion = models.DateTimeField(auto_now_add=True)
    fecha_vencimiento = models.DateTimeField(
        null=True, blank=True, default=fecha_vencimiento_por_defecto,
        help_text="Cuando vence la publicación deja de mostrarse en la web",
    )
    oferta_inicio = models.DateTimeField(null=True, blank=True, help_text="Desde cuándo rige el precio de oferta")
    oferta_fin = models.DateTimeField(null=True, blank=True, help_text="Hasta cuándo rige el precio de oferta")

    objects = ProductoQuerySet.as_manager()

    class Meta:
        ordering = ['-fecha_publicacion']

    def esta_vencida(self):
        return bool(self.fecha_vencimiento and self.fecha_vencimiento <= timezone.now())

    def lugar(self):
        """Donde se compra: la ubicacion que eligio el vendedor al publicar o su puesto principal."""
        if self.ubicacion_id and self.ubicacion and self.ubicacion.vendedor_id == self.productor_id:
            return self.ubicacion
        return getattr(self.productor, 'puesto', None)

    def vendedor_habilitado(self):
        """El comprador va al puesto: solo se muestra si el vendedor ya marco su puesto en el mapa."""
        perfil = getattr(self.productor, 'perfil', None)
        if settings.VERIFICACION_OBLIGATORIA and not (perfil and perfil.puede_vender_publicamente()):
            return False
        return bool(perfil and perfil.rol == 'PRODUCTOR' and self.productor.is_active and hasattr(self.productor, 'puesto'))

    def esta_publicado(self):
        return self.disponible and self.stock > 0 and not self.esta_vencida() and self.vendedor_habilitado()

    def oferta_activa(self):
        """True si el precio de oferta rige ahora mismo (mismas reglas que ofertas_activas())."""
        if not (self.en_oferta and self.precio_oferta and self.precio_oferta < self.precio):
            return False
        if self.oferta_pendiente_pago or not self.esta_publicado():
            return False
        ahora = timezone.now()
        if self.oferta_inicio and self.oferta_inicio > ahora:
            return False
        if self.oferta_fin and self.oferta_fin <= ahora:
            return False
        return True

    def oferta_programada(self):
        """La oferta ya se pago pero todavia no llega su fecha de inicio."""
        return bool(
            self.en_oferta and not self.oferta_pendiente_pago and self.oferta_inicio
            and self.oferta_inicio > timezone.now() and self.esta_publicado()
        )

    def fecha_limite(self):
        """Fecha real en que termina lo que se muestra: la oferta o, si no hay, la publicacion."""
        if self.oferta_activa() and self.oferta_fin:
            if self.fecha_vencimiento and self.fecha_vencimiento < self.oferta_fin:
                return self.fecha_vencimiento
            return self.oferta_fin
        return self.fecha_vencimiento

    def fecha_inicio_periodo(self):
        if self.oferta_activa() and self.oferta_fin and self.oferta_inicio:
            return self.oferta_inicio
        return self.fecha_publicacion

    def porcentaje_tiempo_restante(self):
        """Que porcentaje del tiempo de la publicacion (u oferta) queda, de 0 a 100."""
        limite = self.fecha_limite()
        inicio = self.fecha_inicio_periodo()
        if not limite or not inicio:
            return 100
        total = (limite - inicio).total_seconds()
        restante = (limite - timezone.now()).total_seconds()
        if total <= 0 or restante <= 0:
            return 0
        return max(1, min(100, int(round(restante * 100 / total))))

    def texto_tiempo_restante(self):
        limite = self.fecha_limite()
        if not limite:
            return "Sin fecha límite"
        segundos = int((limite - timezone.now()).total_seconds())
        if segundos <= 0:
            return "Vencida"
        dias, resto = divmod(segundos, 86400)
        horas = resto // 3600
        if dias >= 2:
            return f"Quedan {dias} días"
        if dias == 1:
            return f"Queda 1 día y {horas} h" if horas else "Queda 1 día"
        if horas >= 1:
            return f"Quedan {horas} h"
        return f"Quedan {max(1, resto // 60)} min"

    def nivel_tiempo_restante(self):
        """Color de la barra: ok, medio o poco."""
        limite = self.fecha_limite()
        if not limite:
            return 'ok'
        segundos = (limite - timezone.now()).total_seconds()
        porcentaje = self.porcentaje_tiempo_restante()
        if segundos < 86400 or porcentaje <= 20:
            return 'poco'
        if porcentaje <= 50:
            return 'medio'
        return 'ok'

    def precio_actual(self):
        if self.oferta_activa():
            return self.precio_oferta
        return self.precio

    def ahorro(self):
        if self.oferta_activa():
            return self.precio - self.precio_oferta
        return Decimal('0.00')

    def valor_oferta(self):
        """Valor total del lote en oferta (precio de oferta x stock)."""
        if self.precio_oferta:
            return self.precio_oferta * self.stock
        return Decimal('0.00')

    def monto_comision_oferta(self):
        """Lo que paga el vendedor (publicidad) para que su producto salga como oferta: tarifa fija."""
        return Decimal(str(settings.TARIFA_OFERTA)).quantize(Decimal('0.01'))

    def descuento_configurado(self):
        """Descuento que puso el vendedor, aunque la oferta todavia no este vigente."""
        if self.precio_oferta and self.precio > 0 and self.precio_oferta < self.precio:
            return int(round((self.precio - self.precio_oferta) / self.precio * 100))
        return 0

    def porcentaje_descuento(self):
        if self.oferta_activa():
            return self.descuento_configurado()
        return 0

    def nombre_unidad_stock(self):
        """Devuelve la unidad en formato corto y claro según la cantidad en stock (ej. 'kg', 'cajas', 'sacos', 'toneladas')."""
        unidades_cortas = {
            'KG': ('kg', 'kg'),
            'DOCENA': ('docena', 'docenas'),
            'ATADO': ('atado', 'atados'),
            'BOLSA': ('bolsa', 'bolsas'),
            'SACO': ('saco', 'sacos'),
            'CAJA': ('caja', 'cajas'),
            'ARROBA': ('arroba', 'arrobas'),
            'TONELADA': ('tonelada', 'toneladas'),
        }
        singular, plural = unidades_cortas.get(self.unidad, ('unidad', 'unidades'))
        return singular if self.stock == 1 else plural

    def unidad_corta(self):
        """Unidad en singular para mostrar junto al precio (ej. 'S/ 3.20 / kg')."""
        return {'KG': 'kg', 'DOCENA': 'docena', 'ATADO': 'atado', 'BOLSA': 'bolsa', 'SACO': 'saco', 'CAJA': 'caja', 'ARROBA': 'arroba', 'TONELADA': 'tonelada'}.get(self.unidad, 'unidad')

    def nombre_unidad_minimo(self):
        """Devuelve la unidad según la cantidad mínima de compra."""
        unidades_cortas = {
            'KG': ('kg', 'kg'),
            'DOCENA': ('docena', 'docenas'),
            'ATADO': ('atado', 'atados'),
            'BOLSA': ('bolsa', 'bolsas'),
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
        ('CANCELADA', 'Cancelada'),
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


class VentaPuesto(models.Model):
    """Cada vez que el vendedor marca 'vendí' en su panel: sirve para el resumen del dia."""
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='ventas_puesto')
    vendedor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ventas_puesto')
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=8, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']

    def total(self):
        return self.cantidad * self.precio_unitario


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
        ('SIMULADO', 'Pago de prueba'),
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
    """Registro del pago (demo) que hace el vendedor para publicar un producto como oferta."""
    METODOS = [
        ('YAPE_PLIN', 'Yape / Plin'),
        ('TARJETA', 'Tarjeta de crédito o débito'),
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
        return f"Pago de oferta {self.codigo_transaccion} - {self.producto.nombre} (S/ {self.monto})"


class ResenaProducto(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='resenas')
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    calificacion = models.PositiveSmallIntegerField(default=5)
    comentario = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']


class FotoProducto(models.Model):
    """Fotos extra de un producto (la principal sigue en Producto.imagen). Maximo 4 extra."""
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='fotos')
    imagen = models.FileField(
        upload_to='productos/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
    )
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['orden', 'id']


class Favorito(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favoritos')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='favoritos')
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']
        constraints = [models.UniqueConstraint(fields=['usuario', 'producto'], name='favorito_unico')]


class Conversacion(models.Model):
    """Chat entre un comprador y el vendedor de un producto. Hay una sola por producto y comprador."""
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='conversaciones')
    comprador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chats_como_comprador')
    vendedor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chats_como_vendedor')
    creada = models.DateTimeField(auto_now_add=True)
    actualizada = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-actualizada']
        constraints = [models.UniqueConstraint(fields=['producto', 'comprador'], name='chat_unico_por_producto')]

    def participa(self, usuario):
        return usuario.id in (self.comprador_id, self.vendedor_id)

    def otro(self, usuario):
        return self.vendedor if usuario.id == self.comprador_id else self.comprador

    def no_leidos(self, usuario):
        return self.mensajes.filter(leido=False).exclude(autor=usuario).count()

    def ultimo_mensaje(self):
        return self.mensajes.order_by('-fecha').first()

    def __str__(self):
        return f"{self.comprador} - {self.vendedor} ({self.producto})"


class Mensaje(models.Model):
    conversacion = models.ForeignKey(Conversacion, on_delete=models.CASCADE, related_name='mensajes')
    autor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mensajes_enviados')
    texto = models.TextField(max_length=1000)
    fecha = models.DateTimeField(auto_now_add=True)
    leido = models.BooleanField(default=False)

    class Meta:
        ordering = ['fecha', 'id']


class Notificacion(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones')
    texto = models.CharField(max_length=200)
    enlace = models.CharField(max_length=200, blank=True)
    icono = models.CharField(max_length=40, default='bi-bell')
    leida = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']

    @classmethod
    def avisar(cls, usuario, texto, enlace='', icono='bi-bell'):
        return cls.objects.create(usuario=usuario, texto=texto[:200], enlace=enlace, icono=icono)


# Los documentos de verificacion NO van a la carpeta media (que es publica): solo los ve el administrador
@deconstructible
class AlmacenVerificaciones(FileSystemStorage):
    def __init__(self):
        super().__init__(location=settings.BASE_DIR / 'privado')

    def url(self, name):
        raise NotImplementedError('Los documentos de verificación no tienen URL pública.')


almacen_privado = AlmacenVerificaciones()
EXTENSIONES_DOCUMENTO = ['jpg', 'jpeg', 'png', 'webp', 'pdf']


class VerificacionVendedor(models.Model):
    """Datos que el vendedor envia una sola vez para comprobar que de verdad atiende un puesto en un mercado.
    Lo revisa una persona del equipo en /admin/."""
    TIPOS = [
        ('PERSONA', 'Persona natural'),
        ('ORGANIZACION', 'Negocio con RUC'),
    ]
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='verificacion')
    tipo = models.CharField(max_length=15, choices=TIPOS, default='PERSONA')
    dni = models.CharField('DNI', max_length=8, blank=True)
    ruc = models.CharField('RUC', max_length=11, blank=True)
    nombre_organizacion = models.CharField('Nombre comercial', max_length=150, blank=True)
    celular = models.CharField(max_length=9)
    distrito = models.CharField('Mercado declarado', max_length=120)
    foto_documento = models.FileField(storage=almacen_privado, upload_to='verificaciones/',
                                      validators=[FileExtensionValidator(EXTENSIONES_DOCUMENTO)])
    foto_en_puesto = models.FileField(storage=almacen_privado, upload_to='verificaciones/',
                                      validators=[FileExtensionValidator(EXTENSIONES_DOCUMENTO)])
    constancia_puesto = models.FileField(storage=almacen_privado, upload_to='verificaciones/', blank=True,
                                         validators=[FileExtensionValidator(EXTENSIONES_DOCUMENTO)],
                                         help_text="Carnet o recibo de la asociación del mercado, recibo de merced conductiva o licencia municipal")
    documento_organizacion = models.FileField(storage=almacen_privado, upload_to='verificaciones/', blank=True,
                                              validators=[FileExtensionValidator(EXTENSIONES_DOCUMENTO)])
    declara_puesto = models.BooleanField('Declara que atiende el puesto', default=False)
    certificado_organico = models.FileField(storage=almacen_privado, upload_to='verificaciones/', blank=True,
                                            validators=[FileExtensionValidator(EXTENSIONES_DOCUMENTO)])
    certificadora = models.CharField(max_length=120, blank=True)
    acepta_tratamiento_datos = models.BooleanField('Aceptó el uso de sus datos', default=False)
    fecha_envio = models.DateTimeField('Enviado el', auto_now=True)

    # Lo que el administrador comprobo (se muestra al comprador sin numeros ni archivos)
    revisado_identidad = models.BooleanField('Identidad comprobada', default=False, help_text="El DNI coincide con la persona de la foto")
    revisado_constancia = models.BooleanField('Constancia del puesto válida', default=False, help_text="El carnet, recibo o licencia es del mismo mercado y puesto")
    revisado_organizacion = models.BooleanField('RUC comprobado', default=False, help_text="RUC activo en SUNAT")
    revisado_puesto = models.BooleanField('Foto en el puesto válida', default=False, help_text="Se ve a la persona en su puesto y coincide con el mercado y número marcados en el mapa")
    revisado_organico = models.BooleanField('Certificado orgánico válido', default=False, help_text="Certificado orgánico vigente de un certificador registrado en SENASA")
    motivo_rechazo = models.CharField('Motivo del rechazo (lo verá el vendedor)', max_length=250, blank=True)
    revisado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verificaciones_revisadas')

    class Meta:
        verbose_name = 'verificación de vendedor'
        verbose_name_plural = 'verificaciones de vendedores'

    def documento(self):
        return self.ruc if self.tipo == 'ORGANIZACION' else self.dni

    def comprobado_texto(self):
        """Resumen publico de lo verificado, por ejemplo: 'identidad (DNI), foto en su puesto'."""
        partes = []
        if self.revisado_identidad:
            partes.append('identidad (DNI)')
        if self.revisado_puesto:
            partes.append('foto en su puesto')
        if self.revisado_constancia:
            partes.append('constancia del mercado')
        if self.revisado_organizacion:
            partes.append('RUC activo')
        if self.revisado_organico:
            partes.append('certificado orgánico')
        return ', '.join(partes)

    def __str__(self):
        return f"Verificación de {self.usuario.username}"


def ruc_valido(ruc):
    """Comprueba el formato y el digito verificador del RUC (modulo 11 de SUNAT)."""
    if len(ruc) != 11 or not ruc.isdigit() or ruc[:2] not in ('10', '15', '17', '20'):
        return False
    pesos = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    suma = sum(int(d) * p for d, p in zip(ruc[:10], pesos))
    digito = 11 - (suma % 11)
    if digito == 10:
        digito = 0
    elif digito == 11:
        digito = 1
    return digito == int(ruc[10])


class CuentaSinPagoOferta(models.Model):
    """Correos de vendedores que publican ofertas sin pagar la publicidad.
    Se maneja solo por dentro (admin o comando oferta_gratis), nunca desde la web."""
    correo = models.EmailField('Correo de la cuenta', unique=True)
    nota = models.CharField('Nota', max_length=120, blank=True, help_text='Ej. socio del proyecto, prueba del docente')
    agregado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Cuenta sin pago de oferta'
        verbose_name_plural = 'Cuentas sin pago de oferta'
        ordering = ['correo']

    def __str__(self):
        return self.correo

    def save(self, *args, **kwargs):
        self.correo = (self.correo or '').strip().lower()
        super().save(*args, **kwargs)

    @classmethod
    def incluye(cls, usuario):
        correo = (getattr(usuario, 'email', '') or '').strip()
        return bool(correo) and cls.objects.filter(correo__iexact=correo).exists()


class UbicacionVendedor(models.Model):
    """Otro lugar donde el vendedor tambien vende (ej. una feria o un segundo puesto).
    El puesto principal sigue en Puesto; aqui solo va el punto del mapa y su nombre."""
    vendedor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ubicaciones')
    nombre = models.CharField('Nombre de la ubicación', max_length=100)
    referencia = models.CharField('Referencia', max_length=150, blank=True)
    direccion = models.CharField('Dirección', max_length=200, blank=True)
    latitud = models.DecimalField(max_digits=8, decimal_places=6, validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitud = models.DecimalField(max_digits=9, decimal_places=6, validators=[MinValueValidator(-180), MaxValueValidator(180)])
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Otra ubicación del vendedor'
        verbose_name_plural = 'Otras ubicaciones de vendedores'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    # Mismo uso que Puesto en las plantillas: lo propio del lugar sale de aqui y lo demas del puesto principal
    @property
    def puesto_principal(self):
        return getattr(self.vendedor, 'puesto', None)

    @property
    def numero(self):
        return ''

    @property
    def horario(self):
        return self.puesto_principal.horario if self.puesto_principal else ''

    def titulo_puesto(self):
        return 'Otra ubicación'

    def url_foto(self):
        return self.puesto_principal.url_foto() if self.puesto_principal else '/static/imagenes/finca_productor.jpg'

    def metodos_pago(self):
        return self.puesto_principal.metodos_pago() if self.puesto_principal else []

    def iconos_pago(self):
        return self.puesto_principal.iconos_pago() if self.puesto_principal else []

    def como_llegar(self):
        return 'https://www.google.com/maps/dir/?' + urlencode({
            'api': 1, 'destination': f'{self.latitud},{self.longitud}',
        })

    def mapa_embebido(self):
        return 'https://maps.google.com/maps?' + urlencode({
            'q': f'{self.latitud},{self.longitud}', 'z': 17, 'output': 'embed', 'hl': 'es',
        })
