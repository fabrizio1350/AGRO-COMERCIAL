"""
Fotos de ejemplo para los productos Demo. Son de Wikimedia Commons, con licencia libre (se cita a cada autor
en /informacion/#creditos-fotos). Se usan miniaturas de 500 px, que Wikimedia sirve siempre.
"""

_BASE = 'https://upload.wikimedia.org/wikipedia/commons/thumb/'

# clave: (ruta en Commons, titulo, licencia, autor)
_FOTOS = {
    'rocoto': ('c/cd/Capsicum_pubescens_%28Rocoto%29.JPG', 'Capsicum pubescens (Rocoto)', 'CC BY-SA 4.0', 'Falcodigiada'),
    'aji': ('2/24/Aji_amarillo_fruits_2.jpg', 'Aji amarillo fruits 2', 'CC BY-SA 4.0', 'Frozenmadness'),
    'huacatay': ('e/ef/Tagetes_minuta_head1_%2815756556993%29.jpg', 'Tagetes minuta head1', 'CC BY 2.0', 'Harry Rose'),
    'muna': ('d/df/Minthostachys_mollis_var._mollis_%28Mu%C3%B1a%29.jpg', 'Minthostachys mollis (Muña)', 'CC BY-SA 4.0', 'Chachacomo'),
    'queso': ('4/44/Queso_fresco.JPG', 'Queso fresco', 'CC BY-SA 3.0', 'Geoff'),
    'huevos': ('d/dd/Eggs_in_basket_2020_G1.jpg', 'Eggs in basket 2020', 'CC BY-SA 4.0', 'George Chernilevsky'),
    'pasas': ('7/7d/Raisins_01.jpg', 'Raisins 01', 'CC BY-SA 3.0', 'Paweł Kuźniar'),
    'higos': ('9/91/Dried_figs_%281%29.jpg', 'Dried figs', 'CC BY 2.0', 'François Nguyen'),
    'rosas': ('0/00/Bouquet_de_roses_roses.jpg', 'Bouquet de roses roses', 'CC BY-SA 3.0', 'Jebulon'),
    'alfalfa': ('b/be/Alfalfa_hay_collection.jpg', 'Alfalfa hay collection', 'Dominio público', 'Vabampidis'),
    'plantones': ('6/66/Plantones_de_Quenual.jpg', 'Plantones de Queñual', 'CC BY-SA 3.0', 'Ondando'),
    'cebolla': ('6/61/Market_at_Hildegardplatz_in_Kempten_03.jpg', 'Market at Hildegardplatz in Kempten', 'CC BY-SA 4.0', 'Kritzolina'),
    'platano': ('3/31/Cavendish_banana_from_Maracaibo.jpg', 'Cavendish banana from Maracaibo', 'CC BY-SA 3.0', 'Wilfredor'),
    'manzana': ('1/15/Red_Apple.jpg', 'Red Apple', 'CC BY 2.0', 'Abhijit Tembhekar'),
    'uva': ('5/5e/Wine_grapes03.jpg', 'Wine grapes', 'GFDL 1.2', 'Fir0002'),
    'maiz_morado': ('e/eb/Zea_mays_%27morado%27_MHNT.BOT.2015.34.11.jpg', "Zea mays 'morado'", 'CC BY-SA 3.0', 'Roger Culos'),
    'choclo': ('8/8c/Choclos_peruanos_2018.jpg', 'Choclos peruanos 2018', 'CC BY-SA 4.0', 'MiguelAlanCS'),
    'camote': ('7/74/Sweet_potatoes_2.jpg', 'Sweet potatoes 2', 'CC BY-SA 4.0', 'Melsj'),
    'limon': ('6/68/Lime-Whole-Split.jpg', 'Lime Whole Split', 'CC0', 'Evan-Amos'),
    'lechuga': ('7/7b/Lactuca_sativa_%27Ashbrook%27.jpg', "Lactuca sativa 'Ashbrook'", 'CC BY-SA 4.0', 'DeFacto'),
    'brocoli': ('0/03/Broccoli_and_cross_section_edit.jpg', 'Broccoli and cross section', 'GFDL 1.2', 'Fir0002'),
    'menestras': ('3/3f/Liat_Portal_for_Foodie_Disorder_-_Assorted_Legumes.jpg', 'Assorted Legumes', 'CC BY-SA 4.0', 'HaJunkiyada'),
    'habas': ('a/a1/Liat_Portal_for_Foodie_Disorder_-_Fresh_Fava_Beans.jpg', 'Fresh Fava Beans', 'CC BY-SA 4.0', 'HaJunkiyada'),
}


def foto(clave):
    ruta = _FOTOS[clave][0]
    return f"{_BASE}{ruta}/500px-{ruta.rsplit('/', 1)[1]}"


def creditos():
    """Lista para la pagina de informacion: titulo, autor, licencia y enlace a la ficha en Commons."""
    return [
        {'titulo': titulo, 'autor': autor, 'licencia': licencia,
         'enlace': f"https://commons.wikimedia.org/wiki/File:{ruta.rsplit('/', 1)[1]}"}
        for ruta, titulo, licencia, autor in _FOTOS.values()
    ]
