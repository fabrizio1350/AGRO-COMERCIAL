from django.db import migrations


LUGAR_POR_DEFECTO = 'Arequipa (Cercado), Arequipa'

# Lugar nuevo de los productos de prueba (por nombre)
ORIGEN_PRODUCTOS_DEMO = {
    'Papa Amarilla Tumbay Seleccionada': 'Chiguata, Arequipa',
    'Quinua Blanca Orgánica de Altura': 'Chivay (Caylloma), Arequipa',
    'Zanahoria Fresca de Sierra (Saco 50 kg)': 'Characato, Arequipa',
    'Mandarina Satsuma sin Pepa': 'Valle de Tambo (Islay), Arequipa',
    'Palta Hass de Exportación': 'Majes (Caylloma), Arequipa',
    'Tomate Río Grande Seleccionado': 'La Joya, Arequipa',
}

# Ubicacion nueva de las cuentas de prueba
UBICACION_CUENTAS_DEMO = {
    'productor_mantaro': 'Chiguata, Arequipa',
    'productor_huaral': 'Majes (Caylloma), Arequipa',
    'comprador_lima': 'Cerro Colorado, Arequipa',
}

CATEGORIAS_NUEVAS = [
    ("Legumbres y Menestras", "Frijol, haba, arveja, pallar y lenteja secos o en vaina."),
    ("Ajíes, Rocotos y Condimentos", "Rocoto arequipeño, ají amarillo, panca, ajo y cebolla."),
    ("Hierbas Aromáticas y Medicinales", "Huacatay, muña, orégano, hierba buena y plantas medicinales."),
    ("Lácteos y Quesos", "Leche fresca, queso paria, queso fresco y derivados del campo."),
    ("Forrajes y Pastos", "Alfalfa, avena forrajera y pastos para ganado."),
    ("Semillas y Plantones", "Semillas certificadas y plantones para siembra."),
    ("Frutos Secos y Deshidratados", "Pasas, higos secos, nueces y frutas deshidratadas."),
    ("Flores y Plantas Ornamentales", "Flores de corte y plantas de vivero."),
    ("Huevos y Animales Menores", "Huevos de granja, cuyes y aves de corral."),
]


def pasar_a_arequipa(apps, schema_editor):
    Producto = apps.get_model('mercado', 'Producto')
    PerfilUsuario = apps.get_model('mercado', 'PerfilUsuario')
    Pedido = apps.get_model('mercado', 'Pedido')
    Categoria = apps.get_model('mercado', 'Categoria')

    # Productos: todos con origen en Arequipa
    for producto in Producto.objects.all():
        nuevo = ORIGEN_PRODUCTOS_DEMO.get(producto.nombre)
        if not nuevo and 'Arequipa' not in producto.origen:
            nuevo = LUGAR_POR_DEFECTO
        if nuevo:
            producto.origen = nuevo
            producto.descripcion = producto.descripcion.replace('valle de Huaral', 'Valle de Tambo')
            producto.save(update_fields=['origen', 'descripcion'])

    # Perfiles: compradores y vendedores en Arequipa
    for perfil in PerfilUsuario.objects.select_related('usuario'):
        nuevo = UBICACION_CUENTAS_DEMO.get(perfil.usuario.username)
        if not nuevo and 'Arequipa' not in perfil.ubicacion:
            nuevo = LUGAR_POR_DEFECTO
        if nuevo:
            perfil.ubicacion = nuevo
        if perfil.nombre_finca == 'Asociación Agrícola Valle del Mantaro':
            perfil.nombre_finca = 'Asociación Agrícola Valle de Chiguata'
        perfil.save(update_fields=['ubicacion', 'nombre_finca'])

    # Pedidos: destino dentro de Arequipa
    Pedido.objects.exclude(ciudad_destino__contains='Arequipa').update(ciudad_destino=LUGAR_POR_DEFECTO)

    # Categorias nuevas para publicar
    for nombre, descripcion in CATEGORIAS_NUEVAS:
        Categoria.objects.get_or_create(nombre=nombre, defaults={'descripcion': descripcion})


class Migration(migrations.Migration):

    dependencies = [
        ("mercado", "0006_producto_imagen_lugares_arequipa"),
    ]

    operations = [
        migrations.RunPython(pasar_a_arequipa, migrations.RunPython.noop),
    ]
