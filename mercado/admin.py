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
    CuentaSinPagoOferta,
    UbicacionVendedor,
    CompraTerminada,
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
    """Aqui se revisan los pagos por Yape/Plin: se compara el numero de operacion y el monto con el Yape
    del numero oficial y recien entonces se confirma. Nadie puede crear ni editar pagos a mano."""
    list_display = ('fecha_pago', 'estado', 'monto', 'numero_operacion', 'nombre_pagador', 'producto', 'productor', 'tipo_oferta', 'telefono_destino')
    list_filter = ('estado', 'tipo_oferta')
    search_fields = ('numero_operacion', 'nombre_pagador', 'productor__username', 'codigo_transaccion')
    actions = ['confirmar_pagos', 'rechazar_pagos']
    fields = ('estado', 'monto', 'numero_operacion', 'nombre_pagador', 'telefono_destino', 'producto', 'productor', 'tipo_oferta',
              'codigo_transaccion', 'fecha_pago', 'revisado_por', 'fecha_revision', 'motivo_rechazo')
    readonly_fields = ('estado', 'monto', 'numero_operacion', 'nombre_pagador', 'telefono_destino', 'producto', 'productor',
                       'tipo_oferta', 'codigo_transaccion', 'fecha_pago', 'revisado_por', 'fecha_revision')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description='Confirmar pago (ya vi el dinero en el Yape)')
    def confirmar_pagos(self, request, queryset):
        confirmados = sum(1 for pago in queryset.select_related('producto', 'productor') if pago.confirmar(request.user))
        self.message_user(request, f"{confirmados} pago(s) confirmados. Sus ofertas ya están publicadas.",
                          messages.SUCCESS if confirmados else messages.WARNING)

    @admin.action(description='Rechazar pago (no aparece en el Yape)')
    def rechazar_pagos(self, request, queryset):
        rechazados = sum(1 for pago in queryset.select_related('producto', 'productor') if pago.rechazar(request.user, pago.motivo_rechazo))
        self.message_user(request, f"{rechazados} pago(s) rechazados. Se avisó a cada vendedor.", messages.INFO)


@admin.register(CompraTerminada)
class CompraTerminadaAdmin(admin.ModelAdmin):
    list_display = ('comprador', 'fecha', 'total', 'productos', 'puestos')
    readonly_fields = ('comprador', 'fecha', 'total', 'productos', 'puestos', 'detalle')


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
    """Revision manual: abrir cada archivo, comparar con el puesto marcado en el mapa, marcar lo comprobado y aprobar."""
    list_display = ('usuario', 'distrito', 'dni', 'estado', 'fecha_envio')
    list_filter = ('usuario__perfil__estado_verificacion',)
    search_fields = ('usuario__username', 'usuario__first_name', 'usuario__last_name', 'dni', 'ruc', 'nombre_organizacion', 'distrito')
    readonly_fields = ('usuario', 'tipo', 'dni', 'ruc', 'nombre_organizacion', 'celular', 'distrito', 'puesto_en_mapa',
                       'ver_foto_documento', 'ver_foto_en_puesto', 'ver_constancia_puesto',
                       'declara_puesto', 'acepta_tratamiento_datos', 'fecha_envio', 'enlaces_consulta',
                       'revisado_por')
    fieldsets = (
        ('Datos enviados por el vendedor', {'fields': ('usuario', 'dni', 'celular', 'ruc', 'nombre_organizacion', 'distrito', 'puesto_en_mapa', 'declara_puesto', 'acepta_tratamiento_datos', 'fecha_envio')}),
        ('Archivos (privados, solo personal)', {'fields': ('ver_foto_documento', 'ver_foto_en_puesto', 'ver_constancia_puesto')}),
        ('Dónde comprobar', {'fields': ('enlaces_consulta',)}),
        ('Lo que comprobaste', {'description': 'Marca lo que comprobaste y guarda. Luego, en la lista, elige la acción "Aprobar" o escribe el motivo y usa "Rechazar". Para aprobar hace falta la identidad y la foto en el puesto.', 'fields': ('revisado_identidad', 'revisado_puesto', 'revisado_constancia', 'revisado_organizacion', 'motivo_rechazo', 'revisado_por')}),
    )
    exclude = ('foto_documento', 'foto_en_puesto', 'constancia_puesto', 'documento_organizacion', 'certificado_organico',
               'certificadora', 'revisado_organico')
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

    @admin.display(description='Foto en el puesto')
    def ver_foto_en_puesto(self, obj):
        return self._enlace_archivo(obj, 'foto_en_puesto')

    @admin.display(description='Constancia del puesto')
    def ver_constancia_puesto(self, obj):
        return self._enlace_archivo(obj, 'constancia_puesto')

    @admin.display(description='Puesto en el mapa')
    def puesto_en_mapa(self, obj):
        puesto = getattr(obj.usuario, 'puesto', None)
        if not puesto:
            return 'Todavía no marcó su puesto'
        return format_html('{} · {} · <a href="{}" target="_blank" rel="noopener">Ver en el mapa</a> · <a href="{}" target="_blank" rel="noopener">Foto pública del puesto</a>',
                           puesto.nombre, puesto.titulo_puesto(), puesto.como_llegar(), puesto.url_foto())

    @admin.display(description='Consultas oficiales')
    def enlaces_consulta(self, obj):
        return format_html(
            '<a href="https://e-consultaruc.sunat.gob.pe/" target="_blank" rel="noopener">SUNAT (RUC)</a> · '
            'Compara la foto en el puesto con la foto pública y el número del puesto. Si hay constancia, '
            'revisa que sea del mismo mercado (asociación, merced conductiva o licencia municipal).'
        )

    def save_model(self, request, obj, form, change):
        obj.revisado_por = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description='Aprobar vendedores seleccionados')
    def aprobar(self, request, queryset):
        aprobados = 0
        for verificacion in queryset.select_related('usuario__perfil'):
            # Se exige haber comprobado la identidad y la foto de la persona en su puesto
            if not (verificacion.revisado_identidad and verificacion.revisado_puesto):
                self.message_user(request, f"{verificacion.usuario.username}: marca primero lo que comprobaste (identidad y foto en el puesto).", messages.WARNING)
                continue
            perfil = verificacion.usuario.perfil
            perfil.estado_verificacion = 'VERIFICADO'
            perfil.fecha_verificacion = timezone.now()
            perfil.organico_verificado = verificacion.revisado_organico
            perfil.save()
            verificacion.revisado_por = request.user
            verificacion.motivo_rechazo = ''
            verificacion.save()
            Notificacion.avisar(verificacion.usuario, "¡Tu puesto fue verificado! Tus productos ya muestran la insignia Puesto verificado.",
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
                verificacion.motivo_rechazo = "Alguna foto no se ve bien o no coincide con tu puesto. Revisa y vuelve a enviar."
            verificacion.save()
            Notificacion.avisar(verificacion.usuario, f"Tu verificación necesita una corrección: {verificacion.motivo_rechazo}",
                                reverse('verificacion_vendedor'), 'bi-exclamation-circle')
        self.message_user(request, f"{queryset.count()} verificación(es) devueltas para corregir.", messages.INFO)


@admin.register(CuentaSinPagoOferta)
class CuentaSinPagoOfertaAdmin(admin.ModelAdmin):
    """Correos que publican ofertas sin pagar. Agrega aqui las cuentas que les pasen."""
    list_display = ('correo', 'cuenta', 'nota', 'agregado')
    search_fields = ('correo', 'nota')

    @admin.display(description='Cuenta que usa ese correo')
    def cuenta(self, obj):
        from django.contrib.auth.models import User
        usuario = User.objects.filter(email__iexact=obj.correo).first()
        return usuario.username if usuario else 'Aún nadie se registró con ese correo'


@admin.register(UbicacionVendedor)
class UbicacionVendedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'vendedor', 'direccion', 'creada')
    search_fields = ('nombre', 'vendedor__username', 'vendedor__email', 'direccion')
