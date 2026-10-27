from datetime import datetime, time, timedelta
from django import forms
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import (
    PerfilUsuario, Producto, OfertaNegociacion, Pedido, ResenaProducto,
    OPCIONES_LUGARES, LUGAR_POR_DEFECTO,
)

# Tamaño maximo de la foto que sube el vendedor (ya llega achicada desde el navegador)
TAMANO_MAXIMO_FOTO = 8 * 1024 * 1024


class RegistroUsuarioForm(UserCreationForm):
    first_name = forms.CharField(
        label="Nombres",
        max_length=80,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Juan Carlos'})
    )
    last_name = forms.CharField(
        label="Apellidos",
        max_length=80,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Quispe Mamani'})
    )
    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'})
    )
    rol = forms.ChoiceField(
        label="Tipo de cuenta en la plataforma",
        choices=PerfilUsuario.ROLES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    ruc_dni = forms.CharField(
        label="RUC o DNI del Vendedor",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. 10456789123'})
    )
    telefono = forms.CharField(
        label="Teléfono / Celular",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. 987654321'})
    )
    ubicacion = forms.ChoiceField(
        label="Distrito / Provincia (Arequipa)",
        choices=[('', 'Elige tu distrito en Arequipa')] + OPCIONES_LUGARES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    nombre_finca = forms.CharField(
        label="Nombre de Chacra, Granja o Huerta (Opcional)",
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Opcional (ej. Granja Familiar)'})
    )
    cuenta_bancaria = forms.CharField(
        label="Número de Cuenta en Soles para Depósito (Opcional)",
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Opcional (ej. BCP Soles: 191-12345678-0-99)'})
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Contraseña'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Repite la contraseña'})


def _inicio_del_dia(dia):
    return timezone.make_aware(datetime.combine(dia, time.min))


def _fin_del_dia(dia):
    return timezone.make_aware(datetime.combine(dia, time(23, 59, 59)))


class ProductoForm(forms.ModelForm):
    origen = forms.ChoiceField(
        label="Lugar de origen (Arequipa)",
        choices=OPCIONES_LUGARES,
        initial=LUGAR_POR_DEFECTO,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    # Fechas como dias del calendario; en save() se pasan a fecha y hora de Arequipa
    vence_el = forms.DateField(
        label="La publicación vence el",
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
    )
    oferta_desde = forms.DateField(
        label="Oferta desde",
        required=False,
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
    )
    oferta_hasta = forms.DateField(
        label="Oferta hasta",
        required=False,
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
    )

    class Meta:
        model = Producto
        fields = [
            'categoria', 'nombre', 'fecha_cosecha', 'origen', 'imagen',
            'descripcion', 'precio', 'en_oferta', 'precio_oferta',
            'acepta_ofertas', 'unidad', 'stock', 'minimo_compra', 'disponible'
        ]
        widgets = {
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Camote Morado, Papa Amarilla, Palta...'}),
            'fecha_cosecha': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
            'imagen': forms.FileInput(attrs={'class': 'd-none', 'accept': 'image/jpeg,image/png,image/webp'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe el producto que vas a vender...'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.10', 'min': '0.50', 'placeholder': 'Ej. 3.50'}),
            'en_oferta': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'precio_oferta': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.10', 'min': '0.10', 'placeholder': 'Ej. 2.90'}),
            'acepta_ofertas': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'unidad': forms.Select(attrs={'class': 'form-select'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'minimo_compra': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'disponible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].empty_label = "Elige una categoría"
        self.fields['categoria'].queryset = self.fields['categoria'].queryset.order_by('nombre')

        hoy = timezone.localdate()
        maximo = hoy + timedelta(days=settings.PUBLICACION_DIAS_MAXIMO)
        for campo in ('vence_el', 'oferta_desde', 'oferta_hasta'):
            self.fields[campo].widget.attrs.update({'min': hoy.isoformat(), 'max': maximo.isoformat()})

        instancia = self.instance
        if instancia.pk and instancia.fecha_vencimiento:
            self.fields['vence_el'].initial = timezone.localtime(instancia.fecha_vencimiento).date()
        else:
            self.fields['vence_el'].initial = hoy + timedelta(days=settings.PUBLICACION_DIAS_VIGENCIA)
        if instancia.pk and instancia.oferta_inicio:
            self.fields['oferta_desde'].initial = timezone.localtime(instancia.oferta_inicio).date()
        if instancia.pk and instancia.oferta_fin:
            self.fields['oferta_hasta'].initial = timezone.localtime(instancia.oferta_fin).date()

    def clean_imagen(self):
        imagen = self.cleaned_data.get('imagen')
        if imagen and hasattr(imagen, 'size') and imagen.size > TAMANO_MAXIMO_FOTO:
            raise forms.ValidationError("La foto es muy pesada (máximo 8 MB).")
        return imagen

    def clean(self):
        cleaned_data = super().clean()
        precio = cleaned_data.get('precio')
        en_oferta = cleaned_data.get('en_oferta')
        precio_oferta = cleaned_data.get('precio_oferta')

        if precio is not None and precio <= 0:
            self.add_error('precio', "El precio debe ser mayor a cero.")
        if en_oferta and (not precio_oferta or (precio and precio_oferta >= precio)):
            self.add_error('precio_oferta', "El precio de oferta debe ser menor al precio normal.")

        hoy = timezone.localdate()
        maximo = hoy + timedelta(days=settings.PUBLICACION_DIAS_MAXIMO)
        vence_el = cleaned_data.get('vence_el')
        if vence_el and vence_el < hoy:
            self.add_error('vence_el', "La fecha de vencimiento no puede estar en el pasado.")
        elif vence_el and vence_el > maximo:
            self.add_error('vence_el', f"Una publicación puede durar como máximo {settings.PUBLICACION_DIAS_MAXIMO} días.")

        if en_oferta:
            desde = cleaned_data.get('oferta_desde') or hoy
            hasta = cleaned_data.get('oferta_hasta')
            cleaned_data['oferta_desde'] = desde
            if not hasta:
                self.add_error('oferta_hasta', "Indica hasta qué día dura la oferta.")
            elif hasta < hoy:
                self.add_error('oferta_hasta', "No se puede publicar una oferta que ya venció.")
            elif hasta < desde:
                self.add_error('oferta_hasta', "La oferta debe terminar después de su fecha de inicio.")
            elif vence_el and hasta > vence_el:
                self.add_error('oferta_hasta', "La oferta no puede durar más que la publicación.")
        return cleaned_data

    def save(self, commit=True):
        producto = super().save(commit=False)
        producto.fecha_vencimiento = _fin_del_dia(self.cleaned_data['vence_el'])
        if producto.en_oferta:
            desde = self.cleaned_data['oferta_desde']
            # Si empieza hoy, rige desde este momento y no desde la medianoche
            producto.oferta_inicio = timezone.now() if desde <= timezone.localdate() else _inicio_del_dia(desde)
            producto.oferta_fin = _fin_del_dia(self.cleaned_data['oferta_hasta'])
        else:
            producto.oferta_inicio = None
            producto.oferta_fin = None
        if commit:
            producto.save()
        return producto


class OfertaNegociacionForm(forms.ModelForm):
    class Meta:
        model = OfertaNegociacion
        fields = ['cantidad', 'precio_unitario_ofrecido', 'mensaje']
        widgets = {
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'value': '10'}),
            'precio_unitario_ofrecido': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.10', 'min': '0.10', 'placeholder': 'Precio propuesto S/'}),
            'mensaje': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Compro 20 sacos con recojo inmediato en camión'}),
        }


class PasarelaPagoForm(forms.Form):
    direccion_entrega = forms.CharField(
        label="Dirección exacta de entrega o almacén",
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Av. Andrés Avelino Cáceres, Mercado Avelino Puesto 12'})
    )
    ciudad_destino = forms.ChoiceField(
        label="Distrito de entrega (Arequipa)",
        choices=OPCIONES_LUGARES,
        initial=LUGAR_POR_DEFECTO,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    telefono_contacto = forms.CharField(
        label="Teléfono del receptor",
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. 999888777'})
    )
    metodo_pago = forms.ChoiceField(
        label="Selecciona el Método de Pago",
        choices=Pedido.METODOS_PAGO,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    comentario = forms.CharField(
        label="Instrucciones de transporte o facturación (opcional)",
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Horario de recepción, RUC para guía de remisión, etc.'})
    )


class ResenaForm(forms.ModelForm):
    class Meta:
        model = ResenaProducto
        fields = ['calificacion', 'comentario']
        widgets = {
            'calificacion': forms.Select(
                choices=[(5, '5 Estrellas - Excelente calidad'), (4, '4 Estrellas - Muy bueno'), (3, '3 Estrellas - Regular'), (2, '2 Estrellas - Bajo'), (1, '1 Estrella - Malo')],
                attrs={'class': 'form-select'}
            ),
            'comentario': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Escribe tu opinión sobre la calidad, frescura o atención del productor...'}),
        }


class PerfilForm(forms.ModelForm):
    first_name = forms.CharField(
        label="Nombres",
        max_length=80,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        label="Apellidos",
        max_length=80,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

    ubicacion = forms.ChoiceField(
        label="Distrito / Provincia (Arequipa)",
        choices=[('', 'Elige tu distrito en Arequipa')] + OPCIONES_LUGARES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = PerfilUsuario
        fields = ['rol', 'ruc_dni', 'telefono', 'ubicacion', 'nombre_finca', 'cuenta_bancaria']
        widgets = {
            'rol': forms.Select(attrs={'class': 'form-select'}),
            'ruc_dni': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre_finca': forms.TextInput(attrs={'class': 'form-control'}),
            'cuenta_bancaria': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. BCP Soles: 191-12345678-0-99'}),
        }
