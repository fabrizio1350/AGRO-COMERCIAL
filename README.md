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
3. Copiar `.env.example` a `.env` para el entorno local. Luego aplicar las migraciones:
   ```powershell
   python manage.py migrate
   ```
4. Iniciar el servidor de desarrollo:
   ```powershell
   python manage.py runserver
   ```
5. Abrir en el navegador: `http://127.0.0.1:8000/`

## Cuentas de prueba

Para una demo local, configura `DEBUG=True` y `DATOS_DEMO_AUTOMATICOS=True`.
Las cuentas se crean al abrir el inicio cuando la base aún no tiene productos.

- **Productor Agrícola:**
  - Usuario: `productor_mantaro`
  - Contraseña: `agro12345`
- **Comprador:**
  - Usuario: `comprador_lima`
  - Contraseña: `agro12345`

## Despliegue

- Configura `DEBUG=False`, una `SECRET_KEY` aleatoria de al menos 50 caracteres y los dominios reales en `ALLOWED_HOSTS`. Puedes generar la clave con `python -c "import secrets; print(secrets.token_urlsafe(64))"`.
- Sirve por HTTPS. Si un proxy termina TLS, activa `TRUST_PROXY_HTTPS=True` solo si ese proxy reemplaza `X-Forwarded-Proto` y Django recibe tráfico únicamente desde él.
- Ejecuta `python manage.py migrate`, `python manage.py collectstatic` y `python manage.py check --deploy`. Sirve `staticfiles/` y las fotos públicas de `media/` desde el servidor web. Mantén `privado/` fuera de sus rutas públicas.
- El acceso con Google usa el identificador de la cuenta de Google. Las cuentas creadas con el flujo antiguo requieren asistencia para volver a vincularlas después de verificar su titularidad.
- La web publica productos para compras presenciales. La lista del comprador no reserva stock ni genera pedidos. El vendedor actualiza la cantidad restante desde su panel y el catálogo la consulta cada 5 segundos. Los comprobantes antiguos se conservan como historial.

Configura GOOGLE_MAPS_API_KEY con Maps JavaScript API habilitada y restringida a los dominios de la web para seleccionar el puesto directamente en el mapa. Sin esa clave se pueden pegar coordenadas de Google Maps. El enlace Cómo llegar abre Google Maps con la ubicación guardada.
