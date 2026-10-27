from django.contrib import admin
from .models import (
    PerfilUsuario,
    Categoria,
    Producto,
    OfertaNegociacion,
    ItemCarrito,
    Pedido,
    ResenaProducto,
    PagoComision,
)


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'rol', 'ubicacion', 'telefono', 'nombre_finca')
    list_filter = ('rol',)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'productor', 'categoria', 'precio', 'en_oferta', 'precio_oferta', 'unidad', 'stock', 'disponible', 'oferta_pendiente_pago', 'fecha_vencimiento', 'oferta_fin')
    list_filter = ('categoria', 'en_oferta', 'oferta_pendiente_pago', 'disponible', 'unidad')
    search_fields = ('nombre', 'origen')


@admin.register(OfertaNegociacion)
class OfertaNegociacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'producto', 'comprador', 'cantidad', 'precio_unitario_ofrecido', 'estado', 'fecha_oferta')
    list_filter = ('estado',)


@admin.register(ItemCarrito)
class ItemCarritoAdmin(admin.ModelAdmin):
    list_display = ('comprador', 'producto', 'cantidad', 'precio_unitario_acordado')


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'comprador', 'producto', 'cantidad', 'total', 'metodo_pago', 'estado_pago', 'estado', 'fecha_pedido')
    list_filter = ('estado', 'metodo_pago', 'estado_pago')


@admin.register(PagoComision)
class PagoComisionAdmin(admin.ModelAdmin):
    list_display = ('codigo_transaccion', 'producto', 'productor', 'porcentaje', 'monto', 'metodo_pago', 'fecha_pago')
    list_filter = ('metodo_pago',)


@admin.register(ResenaProducto)
class ResenaProductoAdmin(admin.ModelAdmin):
    list_display = ('producto', 'autor', 'calificacion', 'fecha')
