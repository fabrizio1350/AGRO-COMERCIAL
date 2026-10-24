from django.db import models
from django.contrib.auth.models import User


class PerfilUsuario(models.Model):
    ROLES = [
        ('PRODUCTOR', 'Productor Agrícola'),
        ('COMPRADOR', 'Comprador'),
    ]

    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    rol = models.CharField(max_length=15, choices=ROLES, default='COMPRADOR')
    telefono = models.CharField(max_length=20, blank=True)
    ubicacion = models.CharField(max_length=120, blank=True)
    nombre_finca = models.CharField(max_length=120, blank=True, help_text="Opcional para productores")

    def __str__(self):
        return f"{self.usuario.username} ({self.get_rol_display()})"


class Categoria(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Categorías"

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    UNIDADES = [
        ('KG', 'Kilogramo (kg)'),
        ('SACO', 'Saco (50 kg)'),
        ('CAJA', 'Caja (20 kg)'),
        ('ARROBA', 'Arroba (11.5 kg)'),
    ]

    productor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='productos')
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, related_name='productos')
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField()
    precio = models.DecimalField(max_digits=8, decimal_places=2)
    unidad = models.CharField(max_length=15, choices=UNIDADES, default='KG')
    stock = models.PositiveIntegerField(default=1)
    origen = models.CharField(max_length=120, help_text="Región o valle de cosecha")
    disponible = models.BooleanField(default=True)
    fecha_publicacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_publicacion']

    def __str__(self):
        return f"{self.nombre} - S/ {self.precio} ({self.get_unidad_display()})"


class Pedido(models.Model):
    ESTADOS = [
        ('PENDIENTE', 'Pendiente de confirmación'),
        ('CONFIRMADO', 'Confirmado por el productor'),
        ('EN_CAMINO', 'En camino'),
        ('ENTREGADO', 'Entregado'),
        ('CANCELADO', 'Cancelado'),
    ]

    comprador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='compras')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='pedidos')
    cantidad = models.PositiveIntegerField(default=1)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    direccion_entrega = models.CharField(max_length=200)
    comentario = models.TextField(blank=True)
    estado = models.CharField(max_length=15, choices=ESTADOS, default='PENDIENTE')
    fecha_pedido = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_pedido']

    def __str__(self):
        return f"Pedido #{self.id} - {self.producto.nombre} ({self.comprador.username})"
