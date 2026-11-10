from django.conf import settings
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path
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
    list_display = ('estado_color', 'revisar', 'monto', 'codigo_transaccion', 'numero_operacion', 'nombre_pagador', 'producto', 'productor', 'tipo_oferta', 'fecha_pago')
    list_display_links = None
    list_filter = ('estado', 'tipo_oferta')
    search_fields = ('numero_operacion', 'nombre_pagador', 'productor__username', 'codigo_transaccion')
    actions = ['confirmar_pagos', 'rechazar_pagos']
    change_list_template = 'admin/mercado/ayuda_change_list.html'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description='Estado', ordering='estado')
    def estado_color(self, obj):
        colores = {'PENDIENTE': ('#fdf3ea', '#8f3a10', 'Por confirmar'), 'CONFIRMADO': ('#eef7f0', '#0f4a26', 'Confirmado'),
                   'RECHAZADO': ('#fdecea', '#8a1f15', 'Rechazado')}
        fondo, texto, nombre = colores.get(obj.estado, ('#eee', '#333', obj.estado))
        return format_html('<span style="display:inline-block;padding:3px 10px;border-radius:999px;font-weight:700;white-space:nowrap;'
                           'background:{};color:{};">{}</span>', fondo, texto, nombre)

    @admin.display(description='Qué hacer')
    def revisar(self, obj):
        enlace = reverse('admin:mercado_pagocomision_revisar', args=[obj.pk])
        if obj.estado == 'PENDIENTE':
            return format_html('<a href="{}" style="display:inline-block;padding:5px 12px;border-radius:6px;background:#167a3e;'
                               'color:#fff;font-weight:700;white-space:nowrap;">Revisar y confirmar</a>', enlace)
        return format_html('<a href="{}">Ver detalle</a>', enlace)

    def changelist_view(self, request, extra_context=None):
        pendientes = PagoComision.objects.filter(estado='PENDIENTE').count()
        ayuda = {
            'titulo': f'{pendientes} pago(s) por confirmar. Cómo se confirma un pago:',
            'pasos': [
                f'Abre el Yape o Plin del número {settings.TELEFONO_PAGOS}.',
                'Busca el pago con el mismo N.º de operación y el mismo monto que sale en la lista.',
                'Toca el botón verde "Revisar y confirmar" de ese pago. Al confirmar, la oferta se publica sola y se avisa al vendedor.',
                'Si el pago no aparece en tu Yape, en esa misma pantalla lo rechazas y el vendedor puede enviar otro número.',
            ],
        }
        return super().changelist_view(request, dict(extra_context or {}, ayuda=ayuda))

    def get_urls(self):
        propias = [path('<int:pago_id>/revisar/', self.admin_site.admin_view(self.revisar_pago), name='mercado_pagocomision_revisar')]
        return propias + super().get_urls()

    def change_view(self, request, object_id, form_url='', extra_context=None):
        # Un pago no se edita: se abre la pantalla de revision
        return redirect('admin:mercado_pagocomision_revisar', pago_id=object_id)

    def revisar_pago(self, request, pago_id):
        pago = get_object_or_404(PagoComision.objects.select_related('producto', 'productor', 'revisado_por'), pk=pago_id)
        if request.method == 'POST':
            if not self.has_change_permission(request, pago):
                raise PermissionDenied
            accion = request.POST.get('accion')
            if accion == 'confirmar' and pago.confirmar(request.user):
                self.message_user(request, f'Pago confirmado. La oferta de {pago.producto.nombre} ya está publicada y se avisó al vendedor.', messages.SUCCESS)
            elif accion == 'rechazar' and pago.rechazar(request.user, request.POST.get('motivo', '').strip()):
                self.message_user(request, 'Pago rechazado. Se avisó al vendedor para que revise su número de operación.', messages.WARNING)
            else:
                self.message_user(request, 'Este pago ya había sido revisado.', messages.INFO)
            return redirect(reverse('admin:mercado_pagocomision_changelist') + '?estado__exact=PENDIENTE')
        return render(request, 'admin/mercado/pagocomision/revisar.html', dict(
            self.admin_site.each_context(request), pago=pago, title='Revisar pago', opts=self.model._meta,
            telefono_pagos=settings.TELEFONO_PAGOS,
        ))

    @admin.action(description='Confirmar los pagos marcados (ya vi el dinero en el Yape)')
    def confirmar_pagos(self, request, queryset):
        confirmados = sum(1 for pago in queryset.select_related('producto', 'productor') if pago.confirmar(request.user))
        self.message_user(request, f"{confirmados} pago(s) confirmados. Sus ofertas ya están publicadas.",
                          messages.SUCCESS if confirmados else messages.WARNING)

    @admin.action(description='Rechazar los pagos marcados (no aparecen en el Yape)')
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
    """Correos que publican ofertas premium sin pagar la publicidad (socios, equipo, pruebas del docente)."""
    list_display = ('correo', 'cuenta', 'ofertas_publicadas', 'nota', 'agregado')
    search_fields = ('correo', 'nota')
    change_list_template = 'admin/mercado/ayuda_change_list.html'
    fieldsets = [(None, {
        'fields': ('correo', 'nota'),
        'description': 'Escribe el correo con el que esa persona se registró en MercOfertas. Desde que lo guardes, '
                       'sus ofertas salen como premium sin pasar por el pago, y las que tenía esperando pago se publican al instante.',
    })]

    def usuario_de(self, obj):
        from django.contrib.auth.models import User
        return User.objects.filter(email__iexact=obj.correo).first()

    @admin.display(description='Cuenta que usa ese correo')
    def cuenta(self, obj):
        usuario = self.usuario_de(obj)
        return usuario.username if usuario else 'Aún nadie se registró con ese correo'

    @admin.display(description='Ofertas publicadas gratis')
    def ofertas_publicadas(self, obj):
        usuario = self.usuario_de(obj)
        return Producto.objects.filter(productor=usuario, en_oferta=True, oferta_pendiente_pago=False).count() if usuario else 0

    def changelist_view(self, request, extra_context=None):
        ayuda = {
            'titulo': 'Cuentas que publican ofertas premium gratis',
            'pasos': [
                'Toca "Agregar" (arriba a la derecha) y escribe el correo con el que la persona se registró.',
                'Desde ese momento sus ofertas salen como premium sin pagar, y las que estaban esperando pago se publican solas.',
                'Para que vuelva a pagar, marca su correo en la lista y elige la acción "Eliminar".',
            ],
        }
        return super().changelist_view(request, dict(extra_context or {}, ayuda=ayuda))

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        usuario = self.usuario_de(obj)
        if usuario:
            publicadas = Producto.objects.filter(productor=usuario, en_oferta=True, oferta_pendiente_pago=True).update(
                oferta_pendiente_pago=False, tipo_oferta='PREMIUM')
            self.message_user(request, f'{obj.correo} ya publica ofertas premium gratis. Ofertas publicadas ahora: {publicadas}.', messages.SUCCESS)
        else:
            self.message_user(request, f'Guardado. Todavía nadie se registró con {obj.correo}; cuando lo haga, sus ofertas saldrán gratis.', messages.WARNING)


@admin.register(UbicacionVendedor)
class UbicacionVendedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'vendedor', 'direccion', 'creada')
    search_fields = ('nombre', 'vendedor__username', 'vendedor__email', 'direccion')


admin.site.site_header = 'Administración de MercOfertas'
admin.site.site_title = 'MercOfertas'
admin.site.index_title = 'Qué hay por revisar'
