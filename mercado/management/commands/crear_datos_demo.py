"""
Crea vendedores de mercado y compradores de prueba (con su puesto en el mapa), marcados como Demo.

Uso:
    python manage.py crear_datos_demo          # crea o actualiza los bots
    python manage.py crear_datos_demo --borrar # elimina todos los bots Demo y sus datos

Los bots no pueden iniciar sesion (contraseña inutilizable) y en la web se muestran
con la etiqueta "Demo" para que nadie los confunda con productores reales.
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from django.conf import settings
from django.core.files import File

from mercado.models import Categoria, PerfilUsuario, Producto, Puesto, ResenaProducto, CATEGORIAS_AGRICOLAS

# Cuentas de prueba que ya existian: tambien se marcan como Demo
CUENTAS_DEMO_ANTERIORES = ['productor_mantaro', 'productor_huaral', 'comprador_lima']

# Vendedores de mercado de ejemplo. Los puestos y coordenadas son aproximados y se ven como "Demo".
PRODUCTORES = [
    {
        'usuario': 'demo_productor_characato', 'nombre': 'Rosa', 'apellido': 'Quispe',
        'ubicacion': 'Arequipa (Cercado), Arequipa', 'finca': 'Verduras Rosita (Demo)',
        'puesto': dict(nombre='Mercado San Camilo', numero='112', referencia='Pasillo de verduras, entrada por calle Perú',
                       horario='Lunes a domingo, 6 a. m. a 6 p. m.', lat='-16.401750', lng='-71.533180',
                       foto='tomate.jpg', efectivo=True, tarjeta=False, yape_plin=True),
        'productos': [
            dict(nombre='Tomate italiano', categoria='Hortalizas y Verduras', precio='3.50', oferta='2.80', unidad='KG',
                 stock=35, imagen='/static/imagenes/tomate.jpg',
                 descripcion='Tomate firme y maduro, ideal para ensalada y salsa. Llegó hoy temprano.'),
            dict(nombre='Zanahoria', categoria='Hortalizas y Verduras', precio='2.00', unidad='KG',
                 stock=40, imagen='/static/imagenes/zanahoria.jpg',
                 descripcion='Zanahoria dulce y lavada.'),
        ],
    },
    {
        'usuario': 'demo_productor_chivay', 'nombre': 'Julián', 'apellido': 'Condori',
        'ubicacion': 'Arequipa (Cercado), Arequipa', 'finca': 'Granos Don Julián (Demo)',
        'puesto': dict(nombre='Mercado San Camilo', numero='48', referencia='Zona de abarrotes y granos',
                       horario='Lunes a sábado, 7 a. m. a 5 p. m.', lat='-16.401420', lng='-71.532760',
                       foto='quinua_blanca.jpg', efectivo=True, tarjeta=True, yape_plin=True),
        'productos': [
            dict(nombre='Quinua roja del Colca', categoria='Granos y Cereales', precio='12.00', unidad='KG',
                 stock=25, imagen='/static/imagenes/quinua_blanca.jpg',
                 descripcion='Quinua lavada y lista para cocinar. Se vende por kilo.'),
            dict(nombre='Papa huayro', categoria='Tubérculos y Raíces', precio='3.80', oferta='3.20', unidad='KG',
                 stock=60, imagen='/static/imagenes/papa_amarilla.jpg',
                 descripcion='Papa harinosa, perfecta para sancochado y puré.'),
        ],
    },
    {
        'usuario': 'demo_productor_majes', 'nombre': 'Hugo', 'apellido': 'Valdivia',
        'ubicacion': 'José Luis Bustamante y Rivero, Arequipa', 'finca': 'Frutas Hugo (Demo)',
        'puesto': dict(nombre='Mercado Avelino Cáceres', numero='305', referencia='Nave de frutas, frente a la puerta 3',
                       horario='Todos los días, 5 a. m. a 4 p. m.', lat='-16.423650', lng='-71.520790',
                       foto='palta_hass.jpg', efectivo=True, tarjeta=True, yape_plin=False),
        'productos': [
            dict(nombre='Palta fuerte', categoria='Frutas de Estación', precio='8.00', oferta='6.50', unidad='KG',
                 stock=18, imagen='/static/imagenes/palta_hass.jpg',
                 descripcion='Palta cremosa, madura para hoy y mañana.'),
            dict(nombre='Mandarina', categoria='Frutas de Estación', precio='4.00', unidad='KG',
                 stock=45, imagen='/static/imagenes/mandarina.jpg',
                 descripcion='Mandarina jugosa y dulce.'),
        ],
    },
    {
        'usuario': 'demo_productor_tiabaya', 'nombre': 'Marisol', 'apellido': 'Flores',
        'ubicacion': 'Cerro Colorado, Arequipa', 'finca': 'Puesto Marisol (Demo)',
        'puesto': dict(nombre='Mercado Río Seco', numero='17', referencia='Al lado de las juguerías',
                       horario='Lunes a domingo, 6 a. m. a 2 p. m.', lat='-16.360800', lng='-71.567900',
                       foto='banner_agro.jpg', efectivo=True, tarjeta=False, yape_plin=True),
        'productos': [
            dict(nombre='Tomate redondo', categoria='Hortalizas y Verduras', precio='3.00', oferta='2.50', unidad='KG',
                 stock=8, imagen='/static/imagenes/tomate.jpg',
                 descripcion='Tomate redondo de buen color. Quedan pocos kilos.'),
            dict(nombre='Papa amarilla', categoria='Tubérculos y Raíces', precio='4.50', unidad='KG',
                 stock=30, imagen='/static/imagenes/papa_amarilla.jpg',
                 descripcion='Papa amarilla para causa y frituras.'),
        ],
    },
]

COMPRADORES = [
    {'usuario': 'demo_comprador_restaurante', 'nombre': 'Andrea', 'apellido': 'Paredes',
     'ubicacion': 'Yanahuara, Arequipa', 'empresa': 'Restaurante Demo El Fogón'},
    {'usuario': 'demo_comprador_mercado', 'nombre': 'Luis', 'apellido': 'Mamani',
     'ubicacion': 'Arequipa (Cercado), Arequipa', 'empresa': 'Puesto Demo Mercado San Camilo'},
    {'usuario': 'demo_comprador_distribuidor', 'nombre': 'Carmen', 'apellido': 'Torres',
     'ubicacion': 'Cerro Colorado, Arequipa', 'empresa': 'Distribuidora Demo del Sur'},
]

# Comentarios de los compradores bot: (comprador, nombre del producto, estrellas, texto)
COMENTARIOS = [
    (0, 'Tomate italiano', 5, 'Fui temprano y estaba tal cual la foto.'),
    (1, 'Papa huayro', 4, 'Buena papa, la señora atiende rápido.'),
    (2, 'Palta fuerte', 5, 'Madura justo para el almuerzo.'),
    (0, 'Quinua roja del Colca', 4, 'Grano limpio, aceptan Yape.'),
    (1, 'Tomate redondo', 5, 'Buen precio en oferta.'),
    (2, 'Mandarina', 4, 'Dulces, volveré.'),
]


class Command(BaseCommand):
    help = 'Crea (o borra con --borrar) productores y compradores bot marcados como Demo.'

    def add_arguments(self, parser):
        parser.add_argument('--borrar', action='store_true', help='Elimina todos los bots Demo creados por este comando.')

    @transaction.atomic
    def handle(self, *args, **opciones):
        usuarios_bot = [p['usuario'] for p in PRODUCTORES] + [c['usuario'] for c in COMPRADORES]
        if opciones['borrar']:
            borrados, _ = User.objects.filter(username__in=usuarios_bot).delete()
            self.stdout.write(self.style.WARNING(f'Se eliminaron los bots Demo ({borrados} registros).'))
            return

        for nombre, descripcion in CATEGORIAS_AGRICOLAS:
            Categoria.objects.get_or_create(nombre=nombre, defaults={'descripcion': descripcion})

        marcados = PerfilUsuario.objects.filter(usuario__username__in=CUENTAS_DEMO_ANTERIORES).update(es_demo=True)

        ahora = timezone.now()
        productos = {}
        for datos in PRODUCTORES:
            usuario = self.crear_usuario(datos, 'PRODUCTOR', datos['finca'])
            self.crear_puesto(usuario, datos['puesto'])
            datos['ubicacion'] = datos['puesto']['nombre']
            for prod in datos['productos']:
                valores = dict(
                    categoria=Categoria.objects.get(nombre=prod['categoria']),
                    descripcion=prod['descripcion'],
                    precio=Decimal(prod['precio']),
                    unidad=prod['unidad'],
                    stock=prod['stock'],
                    minimo_compra=1,
                    stock_actualizado=ahora,
                    origen=datos['ubicacion'],
                    imagen_url=prod['imagen'],
                    tipo_cultivo='TRADICIONAL',
                    disponible=True,
                    oferta_pendiente_pago=False,
                    fecha_vencimiento=ahora + timedelta(days=30),
                    en_oferta='oferta' in prod,
                    precio_oferta=Decimal(prod['oferta']) if 'oferta' in prod else None,
                    oferta_inicio=ahora if 'oferta' in prod else None,
                    oferta_fin=None,
                )
                producto, _ = Producto.objects.update_or_create(productor=usuario, nombre=prod['nombre'], defaults=valores)
                productos[prod['nombre']] = producto
            # Quita las publicaciones viejas de mayorista de este bot
            Producto.objects.filter(productor=usuario).exclude(nombre__in=[p['nombre'] for p in datos['productos']]).delete()

        compradores = [self.crear_usuario(datos, 'COMPRADOR', datos['empresa']) for datos in COMPRADORES]
        for indice, nombre_producto, estrellas, texto in COMENTARIOS:
            ResenaProducto.objects.update_or_create(
                producto=productos[nombre_producto], autor=compradores[indice],
                defaults={'calificacion': estrellas, 'comentario': texto},
            )

        self.stdout.write(self.style.SUCCESS(
            f'Listo: {len(PRODUCTORES)} productores Demo, {len(productos)} productos, '
            f'{len(compradores)} compradores Demo y {len(COMENTARIOS)} comentarios. '
            f'Cuentas anteriores marcadas como Demo: {marcados}.'
        ))

    def crear_puesto(self, usuario, datos):
        puesto, _ = Puesto.objects.update_or_create(vendedor=usuario, defaults=dict(
            nombre=datos['nombre'], numero=datos['numero'], referencia=datos['referencia'], horario=datos['horario'],
            latitud=Decimal(datos['lat']), longitud=Decimal(datos['lng']),
            efectivo=datos['efectivo'], tarjeta=datos['tarjeta'], yape_plin=datos['yape_plin'],
            direccion=f"{datos['nombre']}, Arequipa",
        ))
        if not puesto.foto:
            origen = settings.BASE_DIR / 'static' / 'imagenes' / datos['foto']
            with open(origen, 'rb') as archivo:
                puesto.foto.save(f"demo_{usuario.username}.jpg", File(archivo), save=True)
        return puesto

    def crear_usuario(self, datos, rol, nombre_negocio):
        usuario, creado = User.objects.update_or_create(
            username=datos['usuario'],
            defaults={'first_name': datos['nombre'], 'last_name': datos['apellido']},
        )
        if creado:
            # Los bots no inician sesion: solo existen para mostrar datos de ejemplo
            usuario.set_unusable_password()
            usuario.save()
        PerfilUsuario.objects.update_or_create(
            usuario=usuario,
            defaults={'rol': rol, 'ubicacion': datos['ubicacion'], 'nombre_finca': nombre_negocio, 'es_demo': True},
        )
        return usuario
