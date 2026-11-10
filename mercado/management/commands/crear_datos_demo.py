"""
Crea vendedores de mercado y compradores de prueba (con su puesto en el mapa), marcados como Demo,
y algo de movimiento entre ellos: ventas de hoy, favoritos, listas de compras y mensajes.

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

from mercado.models import (
    Categoria, Conversacion, Favorito, ItemCarrito, Mensaje, PerfilUsuario, Producto, Puesto, ResenaProducto,
    VentaPuesto, CATEGORIAS_AGRICOLAS,
)

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
                 descripcion='Zanahoria dulce y lavada.', dias=1),
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
                 descripcion='Quinua lavada y lista para cocinar. Se vende por kilo.', dias=8),
            dict(nombre='Papa huayro', categoria='Tubérculos y Raíces', precio='3.80', oferta='3.20', unidad='KG',
                 stock=60, imagen='/static/imagenes/papa_amarilla.jpg',
                 descripcion='Papa harinosa, perfecta para sancochado y puré.', dias=4,
                 tipo_oferta='NORMAL'),
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
                 descripcion='Palta cremosa, madura para hoy y mañana.', dias=2),
            dict(nombre='Mandarina', categoria='Frutas de Estación', precio='4.00', unidad='KG',
                 stock=45, imagen='/static/imagenes/mandarina.jpg',
                 descripcion='Mandarina jugosa y dulce.', dias=3),
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
                 descripcion='Papa amarilla para causa y frituras.', dias=9),
        ],
    },
    {
        'usuario': 'demo_vendedor_sanmartin', 'nombre': 'Elena', 'apellido': 'Huamaní',
        'ubicacion': 'Arequipa (Cercado), Arequipa', 'finca': 'Frutería Elena (Demo)',
        'puesto': dict(nombre='Mercado San Camilo', numero='201', referencia='Nave de frutas, segundo pasillo',
                       horario='Lunes a domingo, 6 a. m. a 7 p. m.', lat='-16.401980', lng='-71.533560',
                       foto='mandarina.jpg', efectivo=True, tarjeta=True, yape_plin=True),
        'productos': [
            dict(nombre='Mandarina sin pepa', categoria='Frutas de Estación', precio='5.00', oferta='4.00', unidad='KG',
                 stock=50, imagen='/static/imagenes/mandarina.jpg',
                 descripcion='Mandarina dulce, fácil de pelar. Ideal para la lonchera.', dias=1),
            dict(nombre='Palta hass', categoria='Frutas de Estación', precio='9.00', unidad='KG',
                 stock=22, imagen='/static/imagenes/palta_hass.jpg',
                 descripcion='Palta hass de cáscara negra, lista para comer.', dias=2),
            dict(nombre='Tomate cherry', categoria='Hortalizas y Verduras', precio='6.00', oferta='5.00', unidad='KG',
                 stock=12, imagen='/static/imagenes/tomate.jpg',
                 descripcion='Tomatito cherry para ensaladas y piqueos.', tipo_oferta='NORMAL'),
        ],
    },
    {
        'usuario': 'demo_vendedor_altiplano', 'nombre': 'Teófilo', 'apellido': 'Mamani',
        'ubicacion': 'Arequipa (Cercado), Arequipa', 'finca': 'Papas del Altiplano (Demo)',
        'puesto': dict(nombre='Mercado El Altiplano', numero='9', referencia='Entrada principal, a la derecha',
                       horario='Lunes a sábado, 5 a. m. a 3 p. m.', lat='-16.394700', lng='-71.540600',
                       foto='papa_amarilla.jpg', efectivo=True, tarjeta=False, yape_plin=True),
        'productos': [
            dict(nombre='Papa blanca', categoria='Tubérculos y Raíces', precio='2.20', oferta='1.80', unidad='KG',
                 stock=120, imagen='/static/imagenes/papa_amarilla.jpg',
                 descripcion='Papa blanca para el día a día. Por saco o por kilo.', dias=5),
            dict(nombre='Papa canchán', categoria='Tubérculos y Raíces', precio='2.50', unidad='KG',
                 stock=80, imagen='/static/imagenes/papa_amarilla.jpg',
                 descripcion='Papa canchán buena para freír.', dias=6),
        ],
    },
    {
        'usuario': 'demo_vendedor_avelino', 'nombre': 'Carmen', 'apellido': 'Ccama',
        'ubicacion': 'José Luis Bustamante y Rivero, Arequipa', 'finca': 'Verduras Doña Carmen (Demo)',
        'puesto': dict(nombre='Mercado Avelino Cáceres', numero='118', referencia='Nave de verduras, frente a la puerta 1',
                       horario='Todos los días, 4 a. m. a 3 p. m.', lat='-16.423200', lng='-71.521300',
                       foto='zanahoria.jpg', efectivo=True, tarjeta=False, yape_plin=True),
        'productos': [
            dict(nombre='Zanahoria por saco', categoria='Hortalizas y Verduras', precio='1.50', oferta='1.20', unidad='KG',
                 stock=150, imagen='/static/imagenes/zanahoria.jpg',
                 descripcion='Zanahoria mediana, precio especial por cantidad.', dias=2),
            dict(nombre='Tomate de ensalada', categoria='Hortalizas y Verduras', precio='3.20', unidad='KG',
                 stock=40, imagen='/static/imagenes/tomate.jpg',
                 descripcion='Tomate rojo y firme, recién llegado de Majes.'),
        ],
    },
    {
        'usuario': 'demo_vendedor_palomar', 'nombre': 'Wilber', 'apellido': 'Apaza',
        'ubicacion': 'Arequipa (Cercado), Arequipa', 'finca': 'Granos Wilber (Demo)',
        'puesto': dict(nombre='Mercado El Palomar', numero='56', referencia='Pasillo de abarrotes',
                       horario='Lunes a sábado, 7 a. m. a 6 p. m.', lat='-16.410900', lng='-71.528400',
                       foto='quinua_blanca.jpg', efectivo=True, tarjeta=True, yape_plin=True),
        'productos': [
            dict(nombre='Quinua blanca', categoria='Granos y Cereales', precio='10.00', oferta='8.50', unidad='KG',
                 stock=30, imagen='/static/imagenes/quinua_blanca.jpg',
                 descripcion='Quinua blanca lavada, grano grande.', dias=10),
            dict(nombre='Quinua perlada', categoria='Granos y Cereales', precio='11.00', unidad='KG',
                 stock=18, imagen='/static/imagenes/quinua_blanca.jpg',
                 descripcion='Quinua perlada para sopas y postres.', dias=12),
        ],
    },
    {
        'usuario': 'demo_vendedor_ciudadmi', 'nombre': 'Rocío', 'apellido': 'Turpo',
        'ubicacion': 'Paucarpata, Arequipa', 'finca': 'Puesto Rocío (Demo)',
        'puesto': dict(nombre='Mercado de Ciudad Mi Trabajo', numero='73', referencia='Zona de frutas y verduras',
                       horario='Lunes a domingo, 6 a. m. a 4 p. m.', lat='-16.430900', lng='-71.506600',
                       foto='palta_hass.jpg', efectivo=True, tarjeta=False, yape_plin=True),
        'productos': [
            dict(nombre='Palta criolla', categoria='Frutas de Estación', precio='6.00', oferta='4.50', unidad='KG',
                 stock=6, imagen='/static/imagenes/palta_hass.jpg',
                 descripcion='Palta criolla madura. Últimos kilos del día.', dias=3),
            dict(nombre='Mandarina de Chala', categoria='Frutas de Estación', precio='3.50', unidad='KG',
                 stock=35, imagen='/static/imagenes/mandarina.jpg',
                 descripcion='Mandarina jugosa para jugo.', dias=2),
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
    {'usuario': 'demo_comprador_menu', 'nombre': 'Patricia', 'apellido': 'Salas',
     'ubicacion': 'Cayma, Arequipa', 'empresa': 'Menú Demo La Casona'},
    {'usuario': 'demo_comprador_juguera', 'nombre': 'Jhon', 'apellido': 'Chávez',
     'ubicacion': 'Arequipa (Cercado), Arequipa', 'empresa': 'Juguería Demo San Camilo'},
    {'usuario': 'demo_comprador_casa', 'nombre': 'Milagros', 'apellido': 'Pari',
     'ubicacion': 'Miraflores, Arequipa', 'empresa': 'Compras de casa (Demo)'},
    {'usuario': 'demo_comprador_bodega', 'nombre': 'Ronald', 'apellido': 'Quispe',
     'ubicacion': 'Paucarpata, Arequipa', 'empresa': 'Bodega Demo Don Ronald'},
    {'usuario': 'demo_comprador_picanteria', 'nombre': 'Gloria', 'apellido': 'Zúñiga',
     'ubicacion': 'Sachaca, Arequipa', 'empresa': 'Picantería Demo La Lucila'},
]

# Comentarios de los compradores bot: (comprador, nombre del producto, estrellas, texto)
COMENTARIOS = [
    (0, 'Tomate italiano', 5, 'Fui temprano y estaba tal cual la foto.'),
    (1, 'Papa huayro', 4, 'Buena papa, la señora atiende rápido.'),
    (2, 'Palta fuerte', 5, 'Madura justo para el almuerzo.'),
    (0, 'Quinua roja del Colca', 4, 'Grano limpio, aceptan Yape.'),
    (1, 'Tomate redondo', 5, 'Buen precio en oferta.'),
    (2, 'Mandarina', 4, 'Dulces, volveré.'),
    (3, 'Papa blanca', 5, 'Buen precio por saco para el menú.'),
    (4, 'Mandarina sin pepa', 5, 'Salen bastantes jugos, muy dulces.'),
    (5, 'Palta hass', 4, 'Madura, aunque llegué tarde y quedaban pocas.'),
    (6, 'Quinua blanca', 5, 'Grano limpio, la uso para la mazamorra.'),
    (7, 'Zanahoria por saco', 4, 'Llevé un saco, todo buena.'),
    (3, 'Tomate de ensalada', 5, 'Firmes y rojitos.'),
    (4, 'Palta criolla', 4, 'Buena para el desayuno.'),
    (5, 'Tomate cherry', 5, 'Perfectos para la ensalada.'),
    (6, 'Papa huayro', 5, 'Para la ocopa quedó buenaza.'),
    (7, 'Quinua perlada', 4, 'Rinde bastante.'),
]

# Movimiento de ejemplo (todo entre cuentas Demo): ventas de hoy, favoritos, listas de compras y mensajes.
# (comprador, producto, cantidad)
LISTAS = [
    (0, 'Tomate italiano', 5), (0, 'Papa blanca', 10), (3, 'Zanahoria por saco', 8),
    (4, 'Mandarina sin pepa', 6), (5, 'Palta hass', 2), (7, 'Quinua blanca', 3),
]
# (comprador, producto, [mensajes alternando comprador y vendedor])
CHARLAS = [
    (0, 'Tomate italiano', ['Buenas, ¿mañana a las 7 todavía tendrá tomate?', 'Sí, casera, llega temprano. Le separo 5 kilos.']),
    (4, 'Mandarina sin pepa', ['¿Me hace precio si llevo 10 kilos?', 'Le dejo a S/ 3.80 el kilo si viene hoy.', 'Perfecto, paso a las 4.']),
    (3, 'Papa blanca', ['¿Tiene saco de 50 kilos?', 'Sí, me quedan tres sacos.']),
    (6, 'Quinua blanca', ['¿Acepta Yape?', 'Sí, Yape y Plin. Estoy en el puesto 56.']),
]
# Cuantas ventas de hoy tiene cada producto (las horas se reparten en la mañana)
VENTAS_HOY = {
    'Tomate italiano': [3, 2, 5], 'Papa huayro': [4], 'Palta fuerte': [2, 1], 'Mandarina sin pepa': [6, 3, 2],
    'Papa blanca': [10, 5], 'Zanahoria por saco': [8, 4, 2], 'Quinua blanca': [2, 1], 'Palta criolla': [3],
    'Tomate redondo': [2], 'Tomate de ensalada': [5, 2],
}


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
                    tipo_oferta=prod.get('tipo_oferta', 'PREMIUM'),
                    fecha_cosecha=timezone.localdate() - timedelta(days=prod.get('dias', 0)),
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

        movimiento = self.crear_movimiento(productos, compradores)

        self.stdout.write(self.style.SUCCESS(
            f'Listo: {len(PRODUCTORES)} productores Demo, {len(productos)} productos, '
            f'{len(compradores)} compradores Demo y {len(COMENTARIOS)} comentarios. '
            f'Movimiento: {movimiento}. Cuentas anteriores marcadas como Demo: {marcados}.'
        ))

    def crear_movimiento(self, productos, compradores):
        """Ventas de hoy, favoritos, listas y chats entre cuentas Demo. Se rehace cada vez para no duplicar."""
        demo = list(productos.values())
        VentaPuesto.objects.filter(producto__in=demo).delete()
        Favorito.objects.filter(usuario__in=compradores).delete()
        ItemCarrito.objects.filter(comprador__in=compradores).delete()
        Conversacion.objects.filter(comprador__in=compradores).delete()

        inicio_dia = timezone.localtime().replace(hour=6, minute=10, second=0, microsecond=0)
        ventas = 0
        for nombre, cantidades in VENTAS_HOY.items():
            producto = productos[nombre]
            for orden, cantidad in enumerate(cantidades):
                venta = VentaPuesto.objects.create(
                    producto=producto, vendedor=producto.productor, cantidad=cantidad,
                    precio_unitario=producto.precio_actual(),
                )
                # fecha es auto_now_add: se ajusta despues para repartirlas en la manana (nunca en el futuro)
                hora = min(inicio_dia + timedelta(minutes=35 * (orden + 1) + 7 * len(nombre)), timezone.now())
                VentaPuesto.objects.filter(pk=venta.pk).update(fecha=hora)
                ventas += 1

        favoritos = 0
        for indice, comprador in enumerate(compradores):
            for producto in demo[indice::len(compradores)][:3]:
                Favorito.objects.get_or_create(usuario=comprador, producto=producto)
                favoritos += 1

        for indice, nombre, cantidad in LISTAS:
            ItemCarrito.objects.create(comprador=compradores[indice], producto=productos[nombre], cantidad=cantidad)

        for indice, nombre, textos in CHARLAS:
            producto = productos[nombre]
            charla = Conversacion.objects.create(producto=producto, comprador=compradores[indice], vendedor=producto.productor)
            for orden, texto in enumerate(textos):
                autor = charla.comprador if orden % 2 == 0 else charla.vendedor
                Mensaje.objects.create(conversacion=charla, autor=autor, texto=texto, leido=True)

        return (f'{ventas} ventas de hoy, {favoritos} favoritos, {len(LISTAS)} productos en listas '
                f'y {len(CHARLAS)} conversaciones')

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
