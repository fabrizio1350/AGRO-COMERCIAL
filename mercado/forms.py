from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import PerfilUsuario, Producto, Pedido


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
        label="Tipo de cuenta",
        choices=PerfilUsuario.ROLES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    telefono = forms.CharField(
        label="Teléfono / Celular",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. 987654321'})
    )
    ubicacion = forms.CharField(
        label="Ciudad / Región",
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Huancayo, Junín'})
    )
    nombre_finca = forms.CharField(
        label="Nombre de Finca o Asociación (solo productores)",
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Fundo San Isidro'})
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Contraseña segura'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Repite la contraseña'})


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['categoria', 'nombre', 'descripcion', 'precio', 'unidad', 'stock', 'origen', 'disponible']
        widgets = {
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Papa Amarilla Tumbay'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe la calidad, cosecha y características del producto...'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.10', 'min': '0.50'}),
            'unidad': forms.Select(attrs={'class': 'form-select'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'origen': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Huánuco / Valle del Mantaro'}),
            'disponible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_precio(self):
        precio = self.cleaned_data.get('precio')
        if precio is not None and precio <= 0:
            raise forms.ValidationError("El precio debe ser mayor a cero.")
        return precio


class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ['cantidad', 'direccion_entrega', 'comentario']
        widgets = {
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'value': '1'}),
            'direccion_entrega': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dirección exacta o mercado de recepción'}),
            'comentario': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Indicaciones adicionales para el productor o transporte (opcional)'}),
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
        fields = ['rol', 'telefono', 'ubicacion', 'nombre_finca']
        widgets = {
            'rol': forms.Select(attrs={'class': 'form-select'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre_finca': forms.TextInput(attrs={'class': 'form-control'}),
        }
