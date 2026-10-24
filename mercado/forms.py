from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import PerfilUsuario, Producto, OfertaNegociacion, Pedido, ResenaProducto


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
        label="DNI o RUC",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. 10456789123'})
    )
    telefono = forms.CharField(
        label="Teléfono / WhatsApp",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. 987654321'})
    )
    ubicacion = forms.CharField(
        label="Ciudad / Región / Valle",
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Huancayo, Junín'})
    )
    nombre_finca = forms.CharField(
        label="Nombre de Chacra o Asociación (Solo Vendedor)",
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Fundo San Isidro'})
    )
    cuenta_bancaria = forms.CharField(
        label="Número de Cuenta en Soles / CCI (Solo Vendedor)",
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. BCP Soles: 191-12345678-0-99'})
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


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'categoria', 'nombre', 'fecha_cosecha', 'origen', 'imagen_url',
            'descripcion', 'precio', 'en_oferta', 'precio_oferta',
            'acepta_ofertas', 'unidad', 'stock', 'minimo_compra', 'disponible'
        ]
        widgets = {
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Camote Morado, Papa Amarilla, Palta...'}),
            'fecha_cosecha': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
            'origen': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Huaral, Huancayo, Arequipa...'}),
            'imagen_url': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pega aquí el link de una imagen de internet (o déjalo vacío para usar imagen automática)'}),
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

    def clean(self):
        cleaned_data = super().clean()
        precio = cleaned_data.get('precio')
        en_oferta = cleaned_data.get('en_oferta')
        precio_oferta = cleaned_data.get('precio_oferta')

        if precio is not None and precio <= 0:
            self.add_error('precio', "El precio debe ser mayor a cero.")
        if en_oferta and (not precio_oferta or (precio and precio_oferta >= precio)):
            self.add_error('precio_oferta', "El precio de oferta debe ser menor al precio normal.")
        return cleaned_data


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
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Av. La Cultura 450 - Mercado Mayorista Puesto 12'})
    )
    ciudad_destino = forms.CharField(
        label="Ciudad / Región de destino",
        max_length=100,
        initial="Lima Metropolitana",
        widget=forms.TextInput(attrs={'class': 'form-control'})
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

    class Meta:
        model = PerfilUsuario
        fields = ['rol', 'ruc_dni', 'telefono', 'ubicacion', 'nombre_finca', 'cuenta_bancaria']
        widgets = {
            'rol': forms.Select(attrs={'class': 'form-select'}),
            'ruc_dni': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre_finca': forms.TextInput(attrs={'class': 'form-control'}),
            'cuenta_bancaria': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. BCP Soles: 191-12345678-0-99'}),
        }
