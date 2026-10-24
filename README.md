# AgroComercial - Plataforma Web de Comercialización Agrícola

Proyecto universitario desarrollado con **Python y Django** siguiendo una arquitectura **MVT / MVC simple**, base de datos **SQLite** y diseño responsive con **Bootstrap 5**.

## Estructura del Proyecto

- `mercado/models.py`: Modelos de datos (`PerfilUsuario`, `Categoria`, `Producto`, `Pedido`).
- `mercado/views.py`: Controladores y lógica de negocio para catálogo, pedidos, autenticación y panel de productor.
- `mercado/forms.py`: Formularios con validación de datos y estilos de Bootstrap.
- `mercado/urls.py`: Rutas de navegación entre todas las vistas.
- `templates/`: Plantillas HTML conectadas entre sí con recuadros delimitados (`[Espacio para Imagen]`).

## Cómo ejecutar el proyecto localmente

1. Activar el entorno virtual:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
2. Instalar dependencias (si es necesario):
   ```powershell
   pip install -r requirements.txt
   ```
3. Aplicar migraciones de base de datos:
   ```powershell
   python manage.py migrate
   ```
4. Iniciar el servidor de desarrollo:
   ```powershell
   python manage.py runserver
   ```
5. Abrir en el navegador: `http://127.0.0.1:8000/`

## Cuentas de Prueba (se crean automáticamente al abrir el inicio)

- **Productor Agrícola:**
  - Usuario: `productor_mantaro`
  - Contraseña: `agro12345`
- **Comprador:**
  - Usuario: `comprador_lima`
  - Contraseña: `agro12345`
