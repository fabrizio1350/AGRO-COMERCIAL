"""
Crea cuentas bot de prueba (productores y compradores) marcadas como Demo.

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

from mercado.models import Categoria, PerfilUsuario, Producto, ResenaProducto, CATEGORIAS_AGRICOLAS

# Cuentas de prueba que ya existian: tambien se marcan como Demo
CUENTAS_DEMO_ANTERIORES = ['productor_mantaro', 'productor_huaral', 'comprador_lima']

PRODUCTORES = [
    {
        'usuario': 'demo_productor_characato', 'nombre': 'Rosa', 'apellido': 'Quispe',
        'ubicacion': 'Characato, Arequipa', 'finca': 'Huerta Demo Characato',
        'productos': [
            dict(nombre='Tomate Italiano de Huerta', categoria='Hortalizas y Verduras', precio='32.00', unidad='CAJA',
                 stock=40, minimo=2, imagen='/static/imagenes/tomate.jpg',
                 descripcion='Tomate italiano firme, ideal para salsas y restaurantes. Caja de 20 kg.'),
            dict(nombre='Zanahoria Chantenay', categoria='Hortalizas y Verduras', precio='48.00', oferta='42.00', unidad='SACO',
                 stock=25, minimo=1, imagen='/static/imagenes/zanahoria.jpg',
                 descripcion='Zanahoria dulce y de buen color, lavada y seleccionada en sacos de 50 kg.'),
        ],
    },
    {
        'usuario': 'demo_productor_chivay', 'nombre': 'Julián', 'apellido': 'Condori',
        'ubicacion': 'Chivay (Caylloma), Arequipa', 'finca': 'Granos Andinos Demo del Colca',
        'productos': [
            dict(nombre='Quinua Roja del Colca', categoria='Granos y Cereales', precio='11.50', unidad='KG',
                 stock=300, minimo=10, imagen='/static/imagenes/quinua_blanca.jpg', organico=True,
                 descripcion='Quinua roja lavada y venteada, cosechada sobre los 3600 m s. n. m.'),
            dict(nombre='Papa Nativa Huayro', categoria='Tubérculos y Raíces', precio='3.40', oferta='2.90', unidad='KG',
                 stock=600, minimo=20, imagen='/static/imagenes/papa_amarilla.jpg',
                 descripcion='Papa huayro harinosa, perfecta para sancochado y puré.'),
        ],
    },
    {
        'usuario': 'demo_productor_majes', 'nombre': 'Hugo', 'apellido': 'Valdivia',
        'ubicacion': 'Majes (Caylloma), Arequipa', 'finca': 'Fundo Demo Pampa Majes',
        'productos': [
            dict(nombre='Palta Fuerte Calibre 16', categoria='Frutas de Estación', precio='7.20', unidad='KG',
                 stock=400, minimo=15, imagen='/static/imagenes/palta_hass.jpg',
                 descripcion='Palta fuerte de pulpa cremosa, calibre parejo para venta en mercado.'),
            dict(nombre='Mandarina Murcott', categoria='Frutas de Estación', precio='45.00', unidad='CAJA',
                 stock=60, minimo=2, imagen='/static/imagenes/mandarina.jpg',
                 descripcion='Mandarina jugosa y dulce en cajas de 20 kg, recién cosechada.'),
        ],
    },
    {
        'usuario': 'demo_productor_tiabaya', 'nombre': 'Marisol', 'apellido': 'Flores',
        'ubicacion': 'Tiabaya, Arequipa', 'finca': 'Chacra Demo Tiabaya',
        'productos': [
            dict(nombre='Tomate Redondo para Mercado', categoria='Hortalizas y Verduras', precio='29.00', oferta='25.50', unidad='CAJA',
                 stock=50, minimo=2, imagen='/static/imagenes/tomate.jpg',
                 descripcion='Tomate redondo de buen color, en cajas de 20 kg para puestos de mercado.'),
            dict(nombre='Papa Amarilla para Restaurante', categoria='Tubérculos y Raíces', precio='3.10', unidad='KG',
                 stock=800, minimo=50, imagen='/static/imagenes/papa_amarilla.jpg',
                 descripcion='Papa amarilla de calibre mediano, ideal para causa y frituras.'),
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
    (0, 'Tomate Italiano de Huerta', 5, 'Buen calibre y llegó firme, nos sirve para las salsas de la semana.'),
    (1, 'Papa Nativa Huayro', 4, '¿Tienen disponibilidad para la próxima semana? Revisé el lote y se ve bien.'),
    (2, 'Palta Fuerte Calibre 16', 5, 'Calibre parejo como dice la publicación. Consultaré por volumen mayor.'),
    (0, 'Quinua Roja del Colca', 4, 'Grano limpio. Me gustaría saber si la entregan en bolsas de 25 kg.'),
    (1, 'Tomate Redondo para Mercado', 5, 'Buen color, justo lo que piden en el mercado.'),
    (2, 'Mandarina Murcott', 4, 'Revisando precios para pedido de fin de mes.'),
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
            for prod in datos['productos']:
                valores = dict(
                    categoria=Categoria.objects.get(nombre=prod['categoria']),
                    descripcion=prod['descripcion'],
                    precio=Decimal(prod['precio']),
                    unidad=prod['unidad'],
                    stock=prod['stock'],
                    minimo_compra=prod['minimo'],
                    origen=datos['ubicacion'],
                    imagen_url=prod['imagen'],
                    tipo_cultivo='ORGANICO' if prod.get('organico') else 'TRADICIONAL',
                    disponible=True,
                    oferta_pendiente_pago=False,
                    fecha_vencimiento=ahora + timedelta(days=30),
                    en_oferta='oferta' in prod,
                    precio_oferta=Decimal(prod['oferta']) if 'oferta' in prod else None,
                    oferta_inicio=ahora if 'oferta' in prod else None,
                    oferta_fin=ahora + timedelta(days=10) if 'oferta' in prod else None,
                )
                producto, _ = Producto.objects.update_or_create(productor=usuario, nombre=prod['nombre'], defaults=valores)
                productos[prod['nombre']] = producto

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
