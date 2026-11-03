from django.contrib import admin, messages
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from .models import (
    PerfilUsuario,
    Categoria,
    Producto,
    OfertaNegociacion,
    ItemCarrito,
    Pedido,
    ResenaProducto,
    PagoComision,
    FotoProducto,
    Favorito,
    Conversacion,
    Mensaje,
    Notificacion,
    VerificacionVendedor,
)


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'rol', 'estado_verificacion', 'organico_verificado', 'es_demo', 'ubicacion', 'telefono', 'nombre_finca')
    list_filter = ('rol', 'estado_verificacion', 'es_demo')


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


@admin.register(Conversacion)
class ConversacionAdmin(admin.ModelAdmin):
    list_display = ('producto', 'comprador', 'vendedor', 'actualizada')
    search_fields = ('producto__nombre', 'comprador__username', 'vendedor__username')


@admin.register(Mensaje)
class MensajeAdmin(admin.ModelAdmin):
    list_display = ('conversacion', 'autor', 'fecha', 'leido')


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'texto', 'leida', 'fecha')
    list_filter = ('leida',)


admin.site.register(FotoProducto)
admin.site.register(Favorito)


@admin.register(VerificacionVendedor)
class VerificacionVendedorAdmin(admin.ModelAdmin):
    """Revision manual: abrir cada archivo, consultar SUNAT / Padron / SUNARP, marcar lo comprobado y aprobar."""
    list_display = ('usuario', 'tipo', 'documento', 'distrito', 'estado', 'fecha_envio')
    list_filter = ('tipo', 'usuario__perfil__estado_verificacion')
    search_fields = ('usuario__username', 'usuario__first_name', 'usuario__last_name', 'dni', 'ruc', 'nombre_organizacion')
    readonly_fields = ('usuario', 'tipo', 'dni', 'ruc', 'nombre_organizacion', 'celular', 'distrito',
                       'ver_foto_documento', 'ver_foto_chacra', 'ver_documento_organizacion', 'ver_certificado_organico',
                       'inscrito_padron', 'certificadora', 'acepta_tratamiento_datos', 'fecha_envio', 'enlaces_consulta',
                       'revisado_por')
    fieldsets = (
        ('Datos enviados por el vendedor', {'fields': ('usuario', 'tipo', 'dni', 'ruc', 'nombre_organizacion', 'celular', 'distrito', 'inscrito_padron', 'certificadora', 'acepta_tratamiento_datos', 'fecha_envio')}),
        ('Archivos (privados, solo personal)', {'fields': ('ver_foto_documento', 'ver_foto_chacra', 'ver_documento_organizacion', 'ver_certificado_organico')}),
        ('Dónde comprobar', {'fields': ('enlaces_consulta',)}),
        ('Lo que comprobaste', {'description': 'Marca lo que comprobaste y guarda. Luego, en la lista, elige la acción "Aprobar" o escribe el motivo y usa "Rechazar".', 'fields': ('revisado_identidad', 'revisado_padron', 'revisado_organizacion', 'revisado_chacra', 'revisado_organico', 'motivo_rechazo', 'revisado_por')}),
    )
    exclude = ('foto_documento', 'foto_chacra', 'documento_organizacion', 'certificado_organico')
    actions = ['aprobar', 'rechazar']

    @admin.display(description='Estado')
    def estado(self, obj):
        return obj.usuario.perfil.get_estado_verificacion_display()

    def _enlace_archivo(self, obj, campo):
        if not getattr(obj, campo):
            return '—'
        return format_html('<a href="{}" target="_blank" rel="noopener">Abrir archivo</a>',
                           reverse('archivo_verificacion', args=[obj.id, campo]))

    @admin.display(description='Foto del DNI')
    def ver_foto_documento(self, obj):
        return self._enlace_archivo(obj, 'foto_documento')

    @admin.display(description='Foto en la chacra')
    def ver_foto_chacra(self, obj):
        return self._enlace_archivo(obj, 'foto_chacra')

    @admin.display(description='SUNARP / constancia')
    def ver_documento_organizacion(self, obj):
        return self._enlace_archivo(obj, 'documento_organizacion')

    @admin.display(description='Certificado orgánico')
    def ver_certificado_organico(self, obj):
        return self._enlace_archivo(obj, 'certificado_organico')

    @admin.display(description='Consultas oficiales')
    def enlaces_consulta(self, obj):
        return format_html(
            '<a href="https://e-consultaruc.sunat.gob.pe/" target="_blank" rel="noopener">SUNAT (RUC)</a> · '
            '<a href="https://consultapadron.midagri.gob.pe/" target="_blank" rel="noopener">Padrón de Productores (DNI)</a> · '
            '<a href="https://www.sunarp.gob.pe/" target="_blank" rel="noopener">SUNARP</a> · '
            '<a href="https://www.gob.pe/senasa" target="_blank" rel="noopener">SENASA (certificadoras orgánicas)</a>'
        )

    def save_model(self, request, obj, form, change):
        obj.revisado_por = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description='Aprobar vendedores seleccionados')
    def aprobar(self, request, queryset):
        aprobados = 0
        for verificacion in queryset.select_related('usuario__perfil'):
            # Se exige haber comprobado identidad y chacra, y el padron o el registro de la organizacion
            respaldo = verificacion.revisado_organizacion if verificacion.tipo == 'ORGANIZACION' else verificacion.revisado_padron
            if not (verificacion.revisado_identidad and verificacion.revisado_chacra and respaldo):
                self.message_user(request, f"{verificacion.usuario.username}: marca primero lo que comprobaste (identidad, foto en chacra y padrón/SUNARP).", messages.WARNING)
                continue
            perfil = verificacion.usuario.perfil
            perfil.estado_verificacion = 'VERIFICADO'
            perfil.fecha_verificacion = timezone.now()
            perfil.organico_verificado = verificacion.revisado_organico
            perfil.save()
            verificacion.revisado_por = request.user
            verificacion.motivo_rechazo = ''
            verificacion.save()
            Notificacion.avisar(verificacion.usuario, "¡Tu cuenta de vendedor fue verificada! Tus productos ya se muestran a los compradores.",
                                reverse('panel_productor'), 'bi-patch-check-fill')
            aprobados += 1
        if aprobados:
            self.message_user(request, f"{aprobados} vendedor(es) verificados.", messages.SUCCESS)

    @admin.action(description='Rechazar (pedir corrección)')
    def rechazar(self, request, queryset):
        for verificacion in queryset.select_related('usuario__perfil'):
            perfil = verificacion.usuario.perfil
            perfil.estado_verificacion = 'RECHAZADO'
            perfil.organico_verificado = False
            perfil.save()
            verificacion.revisado_por = request.user
            if not verificacion.motivo_rechazo:
                verificacion.motivo_rechazo = "Alguna foto no se ve bien o los datos no coinciden. Revisa y vuelve a enviar."
            verificacion.save()
            Notificacion.avisar(verificacion.usuario, f"Tu verificación necesita una corrección: {verificacion.motivo_rechazo}",
                                reverse('verificacion_vendedor'), 'bi-exclamation-circle')
        self.message_user(request, f"{queryset.count()} verificación(es) devueltas para corregir.", messages.INFO)
