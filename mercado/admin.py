from django.contrib import admin
from .models import PerfilUsuario, Categoria, Producto, Pedido


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'rol', 'ubicacion', 'telefono', 'nombre_finca')
    list_filter = ('rol',)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'productor', 'categoria', 'precio', 'unidad', 'stock', 'disponible')
    list_filter = ('categoria', 'disponible', 'unidad')
    search_fields = ('nombre', 'origen')


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'comprador', 'producto', 'cantidad', 'total', 'estado', 'fecha_pedido')
    list_filter = ('estado',)
