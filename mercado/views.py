import json
import urllib.request
import urllib.parse
import urllib.error
import uuid
from datetime import date, timedelta
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from django.core.paginator import Paginator
from django.db.models import Q, F, Case, When, Count, DecimalField, ExpressionWrapper
from .models import (
    PerfilUsuario,
    Categoria,
    Producto,
    OfertaNegociacion,
    ItemCarrito,
    Pedido,
    ResenaProducto,
    PagoComision,
    CATEGORIAS_AGRICOLAS,
    LUGARES_AREQUIPA,
    LUGAR_POR_DEFECTO,
    OPCIONES_LUGARES,
)
from .forms import (
    RegistroUsuarioForm,
    ProductoForm,
    OfertaNegociacionForm,
    PasarelaPagoForm,
    ResenaForm,
    PerfilForm,
)


def asegurar_datos_iniciales():
    """Crea datos de prueba iniciales si la base de datos esta vacia."""
    if Producto.objects.exists():
        return

    for nombre_cat, descripcion_cat in CATEGORIAS_AGRICOLAS:
        Categoria.objects.get_or_create(nombre=nombre_cat, defaults={"descripcion": descripcion_cat})
    cat_tuberculos = Categoria.objects.get(nombre="Tubérculos y Raíces")
    cat_hortalizas = Categoria.objects.get(nombre="Hortalizas y Verduras")
    cat_frutas = Categoria.objects.get(nombre="Frutas de Estación")
    cat_granos = Categoria.objects.get(nombre="Granos y Cereales")

    productor1, creado1 = User.objects.get_or_create(
        username="productor_mantaro",
        defaults={
            "first_name": "Mateo",
            "last_name": "Huamán",
            "email": "mateo.agromantaro@gmail.com",
        }
    )
    if creado1:
        productor1.set_password("agro12345")
        productor1.save()
        PerfilUsuario.objects.create(
            usuario=productor1,
            rol="PRODUCTOR",
            ruc_dni="10445566771",
            telefono="964112233",
            ubicacion="Chiguata, Arequipa",
            nombre_finca="Asociación Agrícola Valle de Chiguata",
            cuenta_bancaria="BCP Soles: 355-98765432-0-11"
        )
    else:
        p1 = PerfilUsuario.objects.filter(usuario=productor1).first()
        if p1 and not p1.cuenta_bancaria:
            p1.cuenta_bancaria = "BCP Soles: 355-98765432-0-11"
            p1.save()

    productor2, creado2 = User.objects.get_or_create(
        username="productor_huaral",
        defaults={
            "first_name": "Elena",
            "last_name": "Rojas",
            "email": "elena.fundo@gmail.com",
        }
    )
    if creado2:
        productor2.set_password("agro12345")
        productor2.save()
        PerfilUsuario.objects.create(
            usuario=productor2,
            rol="PRODUCTOR",
            ruc_dni="20556677889",
            telefono="945887766",
            ubicacion="Majes (Caylloma), Arequipa",
            nombre_finca="Fundo Santa Elena",
            cuenta_bancaria="BBVA Soles: 0011-0234-0200112233"
        )
    else:
        p2 = PerfilUsuario.objects.filter(usuario=productor2).first()
        if p2 and not p2.cuenta_bancaria:
            p2.cuenta_bancaria = "BBVA Soles: 0011-0234-0200112233"
            p2.save()

    comprador_demo, creado3 = User.objects.get_or_create(
        username="comprador_lima",
        defaults={
            "first_name": "Carlos",
            "last_name": "Mendoza",
            "email": "carlos.comprador@gmail.com",
        }
    )
    if creado3:
        comprador_demo.set_password("agro12345")
        comprador_demo.save()
        PerfilUsuario.objects.create(
            usuario=comprador_demo,
            rol="COMPRADOR",
            ruc_dni="20601122334",
            telefono="999445566",
            ubicacion="Cerro Colorado, Arequipa",
            nombre_finca="Distribuidora Mayorista Mendoza SAC"
        )

    hoy = date.today()
    productos_demo = [
        {
            "productor": productor1,
            "categoria": cat_tuberculos,
            "nombre": "Papa Amarilla Tumbay Seleccionada",
            "variedad": "Amarilla Tumbay",
            "tipo_cultivo": "TRADICIONAL",
            "fecha_cosecha": hoy - timedelta(days=2),
            "calidad": "PRIMERA",
            "descripcion": "Papa amarilla de primera calidad, cosecha reciente libre de químicos agresivos. Ideal para mercados minoristas, pollerías y restaurantes. Empacada en mallas ventiladas.",
            "precio": Decimal("3.80"),
            "en_oferta": True,
            "precio_oferta": Decimal("3.20"),
            "acepta_ofertas": True,
            "unidad": "KG",
            "stock": 450,
            "minimo_compra": 10,
            "origen": "Chiguata, Arequipa",
        },
        {
            "productor": productor1,
            "categoria": cat_granos,
            "nombre": "Quinua Blanca Orgánica de Altura",
            "variedad": "Blanca Seleccionada",
            "tipo_cultivo": "ORGANICO",
            "fecha_cosecha": hoy - timedelta(days=5),
            "calidad": "PRIMERA",
            "descripcion": "Grano seleccionado, limpio y secado de forma natural a más de 3,400 msnm. Alto valor nutritivo, listo para envasado o distribución directa.",
            "precio": Decimal("9.50"),
            "en_oferta": False,
            "precio_oferta": None,
            "acepta_ofertas": True,
            "unidad": "KG",
            "stock": 200,
            "minimo_compra": 5,
            "origen": "Chivay (Caylloma), Arequipa",
        },
        {
            "productor": productor1,
            "categoria": cat_hortalizas,
            "nombre": "Zanahoria Fresca de Sierra (Saco 50 kg)",
            "variedad": "Lavada en saco",
            "tipo_cultivo": "TRADICIONAL",
            "fecha_cosecha": hoy - timedelta(days=1),
            "calidad": "ESTANDAR",
            "descripcion": "Saco de 50 kg de zanahoria fresca recién lavada y clasificada. Excelente resistencia para transporte interprovincial.",
            "precio": Decimal("65.00"),
            "en_oferta": True,
            "precio_oferta": Decimal("54.00"),
            "acepta_ofertas": True,
            "unidad": "SACO",
            "stock": 35,
            "minimo_compra": 1,
            "origen": "Characato, Arequipa",
        },
        {
            "productor": productor2,
            "categoria": cat_frutas,
            "nombre": "Mandarina Satsuma sin Pepa",
            "variedad": "Sin pepa dulce",
            "tipo_cultivo": "INVERNADERO",
            "fecha_cosecha": hoy - timedelta(days=3),
            "calidad": "PRIMERA",
            "descripcion": "Caja de 20 kg de mandarina dulce de exportación, cosechada esta semana en el Valle de Tambo con riego tecnificado.",
            "precio": Decimal("48.00"),
            "en_oferta": True,
            "precio_oferta": Decimal("39.90"),
            "acepta_ofertas": True,
            "unidad": "CAJA",
            "stock": 60,
            "minimo_compra": 2,
            "origen": "Valle de Tambo (Islay), Arequipa",
        },
        {
            "productor": productor2,
            "categoria": cat_frutas,
            "nombre": "Palta Hass de Exportación",
            "variedad": "Hass Firme",
            "tipo_cultivo": "ORGANICO",
            "fecha_cosecha": hoy - timedelta(days=2),
            "calidad": "PRIMERA",
            "descripcion": "Palta Hass con materia seca óptima, piel rugosa y excelente conservación para transporte nacional o mayorista.",
            "precio": Decimal("6.20"),
            "en_oferta": False,
            "precio_oferta": None,
            "acepta_ofertas": True,
            "unidad": "KG",
            "stock": 300,
            "minimo_compra": 15,
            "origen": "Majes (Caylloma), Arequipa",
        },
        {
            "productor": productor2,
            "categoria": cat_hortalizas,
            "nombre": "Tomate Río Grande Seleccionado",
            "variedad": "En caja de 20 kg",
            "tipo_cultivo": "INVERNADERO",
            "fecha_cosecha": hoy,
            "calidad": "ESTANDAR",
            "descripcion": "Caja de 20 kg de tomate firme, maduración uniforme pintón-rojo para distribución directa a mercados y supermercados.",
            "precio": Decimal("42.00"),
            "en_oferta": True,
            "precio_oferta": Decimal("35.00"),
            "acepta_ofertas": True,
            "unidad": "CAJA",
            "stock": 40,
            "minimo_compra": 1,
            "origen": "La Joya, Arequipa",
        },
    ]

    productos_creados = []
    for datos in productos_demo:
        prod = Producto.objects.create(**datos)
        productos_creados.append(prod)

    if productos_creados:
        ResenaProducto.objects.create(
            producto=productos_creados[0],
            autor=comprador_demo,
            calificacion=5,
            comentario="Excelente lote de papa amarilla, llegó puntual y muy bien seleccionada sin tierra."
        )
        OfertaNegociacion.objects.create(
            producto=productos_creados[0],
            comprador=comprador_demo,
            cantidad=50,
            precio_unitario_ofrecido=Decimal("2.90"),
            mensaje="Hola Mateo, te compro 50 kg inmediatos si me dejas a S/ 2.90 el kilo.",
            estado="PENDIENTE"
        )


def ofertas_destacadas(limite=10):
    """Ofertas vigentes para el carrusel: primero las de mayor descuento."""
    return (
        Producto.objects.ofertas_activas()
        .select_related('categoria', 'productor')
        .annotate(descuento_calc=ExpressionWrapper(
            (F('precio') - F('precio_oferta')) * 100 / F('precio'),
            output_field=DecimalField(max_digits=8, decimal_places=2),
        ))
        .order_by('-descuento_calc', 'oferta_fin')[:limite]
    )


def con_precio_vigente(productos):
    """Agrega 'precio_vigente' (oferta si esta activa, si no el normal) para filtrar y ordenar en la base."""
    ids_oferta = Producto.objects.ofertas_activas().values('id')
    return productos.annotate(precio_vigente=Case(
        When(id__in=ids_oferta, then=F('precio_oferta')),
        default=F('precio'),
        output_field=DecimalField(max_digits=8, decimal_places=2),
    ))


def leer_decimal(texto):
    try:
        valor = Decimal(texto)
        return valor if valor >= 0 else None
    except Exception:
        return None


def obtener_o_crear_perfil(usuario):
    perfil, _ = PerfilUsuario.objects.get_or_create(usuario=usuario)
    return perfil


def procesar_cobro_culqi(total_soles, correo_gmail, culqi_token):
    """
    Procesa el cobro en Soles (PEN) usando la API de Culqi (https://api.culqi.com/v2/charges)
    vinculado al correo Gmail del comprador. Si aún no se colocó CULQI_SECRET_KEY en .env,
    ejecuta la simulación de prueba de Culqi para no interrumpir la demostración.
    """
    monto_centimos = int(Decimal(str(total_soles)) * 100)
    secret_key = getattr(settings, 'CULQI_SECRET_KEY', '').strip()

    if secret_key and culqi_token and culqi_token.startswith('tkn_'):
        url = "https://api.culqi.com/v2/charges"
        payload = json.dumps({
            "amount": monto_centimos,
            "currency_code": "PEN",
            "email": correo_gmail,
            "source_id": culqi_token,
            "description": "Compra de productos agricolas en AgroComercial"
        }).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {secret_key}",
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                datos_resp = json.loads(resp.read().decode('utf-8'))
                charge_id = datos_resp.get('id', f"chr_test_{uuid.uuid4().hex[:8]}")
                return True, charge_id, "Cobro procesado en Culqi API"
        except urllib.error.HTTPError as e:
            try:
                err_body = json.loads(e.read().decode('utf-8'))
                msg_err = err_body.get('user_message') or err_body.get('merchant_message') or "Tarjeta rechazada por Culqi."
            except Exception:
                msg_err = "No se pudo completar el cargo en Culqi."
            return False, None, msg_err
        except Exception as e:
            return False, None, f"Error de conexión con Culqi: {e}"

    # Modo Sandbox / Prueba local cuando se usa tarjeta de prueba de Culqi
    codigo_culqi = f"CULQI-CHR-{uuid.uuid4().hex[:6].upper()}"
    return True, codigo_culqi, "Cobro aprobado en Pasarela Culqi (Modo Prueba)"


def enviar_comprobante_gmail(usuario, correo_destino, codigo_tx, lista_pedidos, total_pagar, metodo_pago):
    """
    Envía por correo Gmail la Boleta de Venta Electrónica formal de la compra procesada.
    Usa smtplib directo con las credenciales de .env para que funcione al instante.
    """
    import os
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    if not correo_destino:
        return False

    try:
        primer_ped = lista_pedidos[0] if lista_pedidos else None
        num_correlativo = f"{primer_ped.id:06d}" if primer_ped else "000001"
        serie_boleta = f"B001-{num_correlativo}"
        fecha_emision = timezone.localtime(primer_ped.fecha_pedido).strftime("%d/%m/%Y %H:%M") if primer_ped else timezone.now().strftime("%d/%m/%Y %H:%M")
        nombre_cliente = f"{usuario.first_name} {usuario.last_name}".strip() or usuario.username
        direccion_cliente = f"{primer_ped.direccion_entrega} - {primer_ped.ciudad_destino}" if primer_ped else "Perú"
        telefono_cliente = primer_ped.telefono_contacto if primer_ped else "-"
        subtotal_productos = sum(p.total for p in lista_pedidos)
    except Exception:
        serie_boleta = "B001-000001"
        fecha_emision = "26/10/2026"
        nombre_cliente = usuario.username
        direccion_cliente = "Perú"
        telefono_cliente = "-"
        subtotal_productos = total_pagar

    lineas_productos = "\n".join(
        [
            f"  - [P-{p.producto.id:03d}] {p.cantidad} {p.producto.nombre_unidad_stock().upper()} | "
            f"{p.producto.nombre} (P. Unit: S/ {p.precio_unitario}) -> S/ {p.total}"
            for p in lista_pedidos
        ]
    )

    filas_html = "".join(
        [
            f"<tr>"
            f"<td style='padding:8px 10px;border-bottom:1px solid #e0e0e0;font-size:12px;color:#555;'>AGR-{p.producto.id:03d}</td>"
            f"<td style='padding:8px 10px;border-bottom:1px solid #e0e0e0;font-size:12px;text-align:center;'>{p.cantidad}</td>"
            f"<td style='padding:8px 10px;border-bottom:1px solid #e0e0e0;font-size:12px;text-align:center;'>{p.producto.nombre_unidad_stock().upper()}</td>"
            f"<td style='padding:8px 10px;border-bottom:1px solid #e0e0e0;font-size:12px;'>"
            f"<strong>{p.producto.nombre}</strong><br>"
            f"<span style='color:#666;font-size:11px;'>Origen: {p.producto.origen} | Productor: {p.producto.productor.first_name or p.producto.productor.username}</span>"
            f"</td>"
            f"<td style='padding:8px 10px;border-bottom:1px solid #e0e0e0;font-size:12px;text-align:right;'>S/ {p.precio_unitario}</td>"
            f"<td style='padding:8px 10px;border-bottom:1px solid #e0e0e0;font-size:12px;text-align:right;font-weight:bold;'>S/ {p.total}</td>"
            f"</tr>"
            for p in lista_pedidos
        ]
    )

    asunto = f"Boleta de Venta Electrónica {serie_boleta} ({codigo_tx}) - AgroComercial"
    cuerpo_texto = (
        f"AGROCOMERCIAL PERÚ S.A.C. - RUC: 20608945123\n"
        f"BOLETA DE VENTA ELECTRÓNICA: {serie_boleta}\n"
        f"====================================================\n"
        f"Fecha de Emisión   : {fecha_emision}\n"
        f"Código de Operación: {codigo_tx}\n"
        f"Cliente            : {nombre_cliente}\n"
        f"Correo Electrónico : {correo_destino}\n"
        f"Dirección Entrega  : {direccion_cliente}\n"
        f"Modalidad de Pago  : {metodo_pago}\n"
        f"Moneda             : SOLES (PEN)\n"
        f"====================================================\n"
        f"DETALLE DE LA COMPRA:\n"
        f"{lineas_productos}\n"
        f"  - [SERV-LOG] 1 SERV | Despacho y Guía de Remisión -> S/ 15.00\n"
        f"----------------------------------------------------\n"
        f"OP. EXONERADA (RÉGIMEN AGRARIO) : S/ {subtotal_productos}\n"
        f"SERVICIO DE DESPACHO Y ACOPIO   : S/ 15.00\n"
        f"I.G.V. (0.00% EXONERADO)        : S/ 0.00\n"
        f"IMPORTE TOTAL PAGADO            : S/ {total_pagar}\n"
        f"====================================================\n"
        f"Representación impresa de la Boleta de Venta Electrónica.\n"
        f"Gracias por su preferencia en AgroComercial."
    )

    cuerpo_html = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 680px; margin: 0 auto; border: 1px solid #cfd6cf; background-color: #ffffff; color: #222222;">
        <!-- Cabecera Formal tipo SUNAT -->
        <table style="width: 100%; border-collapse: collapse; padding: 20px; border-bottom: 2px solid #264a32;">
            <tr>
                <td style="padding: 20px; vertical-align: top; width: 60%;">
                    <div style="font-size: 18px; font-weight: bold; color: #264a32; letter-spacing: 0.5px;">AGROCOMERCIAL PERÚ S.A.C.</div>
                    <div style="font-size: 12px; color: #555; margin-top: 4px;">Plataforma de Comercialización Agrícola Directa del Productor</div>
                    <div style="font-size: 11px; color: #666; margin-top: 2px;">Av. Ejército 1020, Cayma - Arequipa | Central: (054) 640-889</div>
                    <div style="font-size: 11px; color: #666;">Correo: facturacion@agrocomercial.pe</div>
                </td>
                <td style="padding: 20px; vertical-align: top; width: 40%; text-align: center;">
                    <div style="border: 2px solid #264a32; border-radius: 4px; padding: 10px 8px; background-color: #f8fbf8;">
                        <div style="font-size: 12px; font-weight: bold; color: #222;">R.U.C. N° 20608945123</div>
                        <div style="font-size: 13px; font-weight: bold; color: #ffffff; background-color: #264a32; margin: 6px -8px; padding: 4px 0;">
                            BOLETA DE VENTA ELECTRÓNICA
                        </div>
                        <div style="font-size: 14px; font-weight: bold; color: #264a32;">N° {serie_boleta}</div>
                    </div>
                </td>
            </tr>
        </table>

        <!-- Datos del Cliente y de la Operacion -->
        <div style="padding: 16px 20px;">
            <table style="width: 100%; border-collapse: collapse; font-size: 12px; background-color: #fafafa; border: 1px solid #e2e5e2;">
                <tr>
                    <td style="padding: 7px 12px; border-bottom: 1px solid #eaeaea; width: 22%; color: #555;"><strong>SEÑOR(ES):</strong></td>
                    <td style="padding: 7px 12px; border-bottom: 1px solid #eaeaea; width: 33%;">{nombre_cliente}</td>
                    <td style="padding: 7px 12px; border-bottom: 1px solid #eaeaea; width: 20%; color: #555;"><strong>FECHA EMISIÓN:</strong></td>
                    <td style="padding: 7px 12px; border-bottom: 1px solid #eaeaea; width: 25%;">{fecha_emision}</td>
                </tr>
                <tr>
                    <td style="padding: 7px 12px; border-bottom: 1px solid #eaeaea; color: #555;"><strong>CORREO CLIENTE:</strong></td>
                    <td style="padding: 7px 12px; border-bottom: 1px solid #eaeaea;">{correo_destino}</td>
                    <td style="padding: 7px 12px; border-bottom: 1px solid #eaeaea; color: #555;"><strong>CÓD. OPERACIÓN:</strong></td>
                    <td style="padding: 7px 12px; border-bottom: 1px solid #eaeaea;"><strong>{codigo_tx}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 7px 12px; border-bottom: 1px solid #eaeaea; color: #555;"><strong>DIRECCIÓN ENTREGA:</strong></td>
                    <td style="padding: 7px 12px; border-bottom: 1px solid #eaeaea;">{direccion_cliente}</td>
                    <td style="padding: 7px 12px; border-bottom: 1px solid #eaeaea; color: #555;"><strong>MONEDA:</strong></td>
                    <td style="padding: 7px 12px; border-bottom: 1px solid #eaeaea;">SOLES (PEN)</td>
                </tr>
                <tr>
                    <td style="padding: 7px 12px; color: #555;"><strong>MEDIO DE PAGO:</strong></td>
                    <td style="padding: 7px 12px;">{metodo_pago}</td>
                    <td style="padding: 7px 12px; color: #555;"><strong>TELÉFONO:</strong></td>
                    <td style="padding: 7px 12px;">{telefono_cliente}</td>
                </tr>
            </table>
        </div>

        <!-- Tabla de Items -->
        <div style="padding: 0 20px 16px 20px;">
            <table style="width: 100%; border-collapse: collapse; border: 1px solid #d5dbd5;">
                <thead>
                    <tr style="background-color: #264a32; color: #ffffff; font-size: 11px; text-transform: uppercase;">
                        <th style="padding: 8px 10px; text-align: left;">Código</th>
                        <th style="padding: 8px 10px; text-align: center;">Cant.</th>
                        <th style="padding: 8px 10px; text-align: center;">Unid.</th>
                        <th style="padding: 8px 10px; text-align: left;">Descripción del Producto</th>
                        <th style="padding: 8px 10px; text-align: right;">P. Unit.</th>
                        <th style="padding: 8px 10px; text-align: right;">Importe</th>
                    </tr>
                </thead>
                <tbody>
                    {filas_html}
                    <tr>
                        <td style="padding: 8px 10px; border-bottom: 1px solid #e0e0e0; font-size: 12px; color: #555;">SERV-LOG</td>
                        <td style="padding: 8px 10px; border-bottom: 1px solid #e0e0e0; font-size: 12px; text-align: center;">1</td>
                        <td style="padding: 8px 10px; border-bottom: 1px solid #e0e0e0; font-size: 12px; text-align: center;">SERV</td>
                        <td style="padding: 8px 10px; border-bottom: 1px solid #e0e0e0; font-size: 12px;">
                            <strong>Servicio de Despacho, Acopio y Guía de Remisión Agrícola</strong>
                        </td>
                        <td style="padding: 8px 10px; border-bottom: 1px solid #e0e0e0; font-size: 12px; text-align: right;">S/ 15.00</td>
                        <td style="padding: 8px 10px; border-bottom: 1px solid #e0e0e0; font-size: 12px; text-align: right; font-weight: bold;">S/ 15.00</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- Totales y Pie de Boleta -->
        <div style="padding: 0 20px 20px 20px;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="width: 55%; vertical-align: top; padding-right: 15px; font-size: 11px; color: #666;">
                        <div style="border: 1px dashed #c5cec5; padding: 10px; background-color: #fbfcfb;">
                            <strong>OBSERVACIONES LEGALES:</strong><br>
                            • Bienes agrícolas exonerados del IGV según Apéndice I de la Ley del IGV.<br>
                            • Representación impresa de la <strong>Boleta de Venta Electrónica {serie_boleta}</strong>.<br>
                            • Código de autorización pasarela: <strong>{codigo_tx}</strong>
                        </div>
                    </td>
                    <td style="width: 45%; vertical-align: top;">
                        <table style="width: 100%; border-collapse: collapse; font-size: 12px; border: 1px solid #d5dbd5;">
                            <tr>
                                <td style="padding: 6px 10px; border-bottom: 1px solid #eaeaea; text-align: right; color: #555;">OP. EXONERADA (S/):</td>
                                <td style="padding: 6px 10px; border-bottom: 1px solid #eaeaea; text-align: right; font-weight: bold;">S/ {subtotal_productos}</td>
                            </tr>
                            <tr>
                                <td style="padding: 6px 10px; border-bottom: 1px solid #eaeaea; text-align: right; color: #555;">DESPACHO Y GUÍA (S/):</td>
                                <td style="padding: 6px 10px; border-bottom: 1px solid #eaeaea; text-align: right; font-weight: bold;">S/ 15.00</td>
                            </tr>
                            <tr>
                                <td style="padding: 6px 10px; border-bottom: 1px solid #eaeaea; text-align: right; color: #555;">I.G.V. (0.00%):</td>
                                <td style="padding: 6px 10px; border-bottom: 1px solid #eaeaea; text-align: right; font-weight: bold;">S/ 0.00</td>
                            </tr>
                            <tr style="background-color: #264a32; color: #ffffff; font-size: 14px;">
                                <td style="padding: 8px 10px; text-align: right; font-weight: bold;">IMPORTE TOTAL:</td>
                                <td style="padding: 8px 10px; text-align: right; font-weight: bold;">S/ {total_pagar}</td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </div>
    </div>
    """

    # Recargar .env en caliente por si se acaba de actualizar sin reiniciar el servidor
    env_file = settings.BASE_DIR / '.env'
    if env_file.exists():
        for lin in env_file.read_text(encoding='utf-8').splitlines():
            if '=' in lin and not lin.strip().startswith('#'):
                k, v = lin.split('=', 1)
                if v.strip():
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")

    remitente_gmail = (os.environ.get('EMAIL_HOST_USER') or getattr(settings, 'EMAIL_HOST_USER', '') or correo_destino).strip()
    clave_app_gmail = (os.environ.get('EMAIL_HOST_PASSWORD') or getattr(settings, 'EMAIL_HOST_PASSWORD', '')).strip().replace(' ', '')

    if remitente_gmail and clave_app_gmail:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = asunto
            msg['From'] = f"AgroComercial <{remitente_gmail}>"
            msg['To'] = correo_destino
            msg.attach(MIMEText(cuerpo_texto, 'plain', 'utf-8'))
            msg.attach(MIMEText(cuerpo_html, 'html', 'utf-8'))

            try:
                with smtplib.SMTP('smtp.gmail.com', 587, timeout=7) as server:
                    server.starttls()
                    server.login(remitente_gmail, clave_app_gmail)
                    server.sendmail(remitente_gmail, [correo_destino], msg.as_string())
                return True
            except Exception:
                with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=7) as server_ssl:
                    server_ssl.login(remitente_gmail, clave_app_gmail)
                    server_ssl.sendmail(remitente_gmail, [correo_destino], msg.as_string())
                return True
        except Exception as e:
            print(f"Error SMTP Gmail: {e}")
            return False
    return False


def inicio(request):
    """Portada publica: hero, categorias, ofertas, productos, como funciona y productores."""
    asegurar_datos_iniciales()
    publicados = Producto.objects.publicados()
    ofertas = ofertas_destacadas()
    productores = (
        PerfilUsuario.objects.filter(rol='PRODUCTOR')
        .select_related('usuario')
        .annotate(total_publicados=Count(
            'usuario__productos',
            filter=Q(usuario__productos__in=publicados),
        ))
        .filter(total_publicados__gt=0)
        .order_by('-total_publicados')[:6]
    )

    contexto = {
        'categorias': Categoria.objects.order_by('nombre'),
        'productos_destacados': publicados.select_related('categoria', 'productor')[:8],
        'ofertas_carrusel': ofertas,
        'mejor_oferta': ofertas[0] if ofertas else None,
        'productores_destacados': productores,
        # Cifras reales sacadas de la base de datos
        'total_productos': publicados.count(),
        'total_ofertas': Producto.objects.ofertas_activas().count(),
        'total_productores': PerfilUsuario.objects.filter(rol='PRODUCTOR').count(),
        'total_distritos': publicados.values('origen').distinct().count(),
    }
    return render(request, 'inicio.html', contexto)


def informacion(request):
    """Preguntas frecuentes, terminos, privacidad y contacto."""
    return render(request, 'informacion.html')


def catalogo(request):
    """Marketplace Agricola completo con buscador, filtros combinados, ordenamiento y paginas."""
    asegurar_datos_iniciales()
    productos = con_precio_vigente(Producto.objects.publicados().select_related('categoria', 'productor'))
    categorias = Categoria.objects.all()

    busqueda = request.GET.get('q', '').strip()
    categoria_id = request.GET.get('categoria', '').strip()
    productor_id = request.GET.get('productor', '').strip()
    unidad = request.GET.get('unidad', '').strip()
    tipo_cultivo = request.GET.get('cultivo', '').strip()
    ubicacion = request.GET.get('ubicacion', '').strip()
    solo_ofertas = request.GET.get('ofertas', '').strip()
    precio_min = request.GET.get('precio_min', '').strip()
    precio_max = request.GET.get('precio_max', '').strip()
    cantidad_min = request.GET.get('cantidad_min', '').strip()
    orden = request.GET.get('orden', 'recientes').strip()

    if busqueda:
        productos = productos.filter(
            Q(nombre__icontains=busqueda) |
            Q(descripcion__icontains=busqueda) |
            Q(origen__icontains=busqueda) |
            Q(variedad__icontains=busqueda)
        )
    if categoria_id.isdigit():
        productos = productos.filter(categoria_id=int(categoria_id))
    if productor_id.isdigit():
        productos = productos.filter(productor_id=int(productor_id))
    if unidad:
        productos = productos.filter(unidad=unidad)
    if tipo_cultivo:
        productos = productos.filter(tipo_cultivo=tipo_cultivo)
    if ubicacion in LUGARES_AREQUIPA:
        productos = productos.filter(origen=ubicacion)
    if solo_ofertas == '1':
        productos = productos.filter(id__in=Producto.objects.ofertas_activas().values('id'))
    valor_min = leer_decimal(precio_min)
    if valor_min is not None:
        productos = productos.filter(precio_vigente__gte=valor_min)
    valor_max = leer_decimal(precio_max)
    if valor_max is not None:
        productos = productos.filter(precio_vigente__lte=valor_max)
    if cantidad_min.isdigit():
        productos = productos.filter(stock__gte=int(cantidad_min))

    if orden == 'precio_asc':
        productos = productos.order_by('precio_vigente')
    elif orden == 'precio_desc':
        productos = productos.order_by('-precio_vigente')
    elif orden == 'stock':
        productos = productos.order_by('-stock')
    elif orden == 'vence':
        productos = productos.order_by('fecha_vencimiento')
    else:
        orden = 'recientes'
        productos = productos.order_by('-fecha_publicacion')

    pagina = Paginator(productos, 12).get_page(request.GET.get('pagina'))
    # Para que los links de pagina conserven los filtros
    parametros = request.GET.copy()
    parametros.pop('pagina', None)

    contexto = {
        'productos': pagina,
        'pagina': pagina,
        'parametros_filtro': parametros.urlencode(),
        'total_resultados': pagina.paginator.count,
        'ofertas_carrusel': ofertas_destacadas(),
        'categorias': categorias,
        'unidades': Producto.UNIDADES,
        'tipos_cultivo': Producto.TIPOS_CULTIVO,
        'lugares': OPCIONES_LUGARES,
        'busqueda': busqueda,
        'categoria_seleccionada': categoria_id,
        'productor_seleccionado': productor_id,
        'unidad_seleccionada': unidad,
        'cultivo_seleccionado': tipo_cultivo,
        'ubicacion_seleccionada': ubicacion,
        'solo_ofertas': solo_ofertas,
        'precio_min': precio_min,
        'precio_max': precio_max,
        'cantidad_min': cantidad_min,
        'orden_seleccionado': orden,
    }
    return render(request, 'catalogo.html', contexto)


def ventas_por_oferta(request):
    """Pagina de ofertas: carrusel destacado, ofertas vigentes con filtros y propuestas de precio."""
    asegurar_datos_iniciales()
    busqueda = request.GET.get('q', '').strip()
    categoria_id = request.GET.get('categoria', '').strip()
    ubicacion = request.GET.get('ubicacion', '').strip()
    unidad = request.GET.get('unidad', '').strip()
    precio_min = request.GET.get('precio_min', '').strip()
    precio_max = request.GET.get('precio_max', '').strip()
    descuento_min = request.GET.get('descuento_min', '').strip()
    cantidad_min = request.GET.get('cantidad_min', '').strip()
    orden = request.GET.get('orden', 'descuento').strip()
    categorias = Categoria.objects.all()

    productos_remate = Producto.objects.ofertas_activas().select_related('categoria', 'productor').annotate(
        descuento_calc=ExpressionWrapper(
            (F('precio') - F('precio_oferta')) * 100 / F('precio'),
            output_field=DecimalField(max_digits=8, decimal_places=2),
        )
    )
    productos_negociables = Producto.objects.publicados().filter(acepta_ofertas=True).select_related('categoria')

    if busqueda:
        filtro_q = Q(nombre__icontains=busqueda) | Q(origen__icontains=busqueda) | Q(descripcion__icontains=busqueda)
        productos_remate = productos_remate.filter(filtro_q)
        productos_negociables = productos_negociables.filter(filtro_q)
    if categoria_id.isdigit():
        productos_remate = productos_remate.filter(categoria_id=int(categoria_id))
        productos_negociables = productos_negociables.filter(categoria_id=int(categoria_id))
    if ubicacion in LUGARES_AREQUIPA:
        productos_remate = productos_remate.filter(origen=ubicacion)
        productos_negociables = productos_negociables.filter(origen=ubicacion)
    if unidad:
        productos_remate = productos_remate.filter(unidad=unidad)
        productos_negociables = productos_negociables.filter(unidad=unidad)
    valor_min = leer_decimal(precio_min)
    if valor_min is not None:
        productos_remate = productos_remate.filter(precio_oferta__gte=valor_min)
    valor_max = leer_decimal(precio_max)
    if valor_max is not None:
        productos_remate = productos_remate.filter(precio_oferta__lte=valor_max)
    if descuento_min.isdigit():
        productos_remate = productos_remate.filter(descuento_calc__gte=int(descuento_min))
    if cantidad_min.isdigit():
        productos_remate = productos_remate.filter(stock__gte=int(cantidad_min))
        productos_negociables = productos_negociables.filter(stock__gte=int(cantidad_min))

    if orden == 'precio_asc':
        productos_remate = productos_remate.order_by('precio_oferta')
    elif orden == 'precio_desc':
        productos_remate = productos_remate.order_by('-precio_oferta')
    elif orden == 'vence':
        productos_remate = productos_remate.order_by(F('oferta_fin').asc(nulls_last=True), 'fecha_vencimiento')
    elif orden == 'recientes':
        productos_remate = productos_remate.order_by('-oferta_inicio', '-fecha_publicacion')
    else:
        orden = 'descuento'
        productos_remate = productos_remate.order_by('-descuento_calc')

    hay_filtros = any([busqueda, categoria_id, ubicacion, unidad, precio_min, precio_max, descuento_min, cantidad_min])

    mis_ofertas_enviadas = []
    ofertas_recibidas_vendedor = []
    if request.user.is_authenticated:
        mis_ofertas_enviadas = OfertaNegociacion.objects.filter(comprador=request.user).select_related('producto', 'producto__productor')
        ofertas_recibidas_vendedor = OfertaNegociacion.objects.filter(producto__productor=request.user).select_related('producto', 'comprador')

    contexto = {
        'productos_remate': productos_remate,
        'productos_negociables': productos_negociables,
        'mis_ofertas_enviadas': mis_ofertas_enviadas,
        'ofertas_recibidas_vendedor': ofertas_recibidas_vendedor,
        'categorias': categorias,
        'ofertas_carrusel': ofertas_destacadas(),
        'unidades': Producto.UNIDADES,
        'lugares': OPCIONES_LUGARES,
        'busqueda': busqueda,
        'categoria_id': categoria_id,
        'ubicacion_seleccionada': ubicacion,
        'unidad_seleccionada': unidad,
        'precio_min': precio_min,
        'precio_max': precio_max,
        'descuento_min': descuento_min,
        'cantidad_min': cantidad_min,
        'orden_seleccionado': orden,
        'hay_filtros': hay_filtros,
    }
    return render(request, 'ofertas.html', contexto)


def detalle_producto(request, producto_id):
    """Apartado completo de descripcion del producto, ficha tecnica, compras, ofertas y resenas."""
    asegurar_datos_iniciales()
    producto = get_object_or_404(Producto, id=producto_id)
    relacionados = Producto.objects.publicados().filter(
        categoria=producto.categoria,
    ).exclude(id=producto.id)[:3]
    resenas = producto.resenas.select_related('autor').all()

    oferta_form = OfertaNegociacionForm(initial={'cantidad': max(producto.minimo_compra, 10)})
    resena_form = ResenaForm()

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.warning(request, "Inicia sesión como Comprador o Vendedor para realizar esta acción.")
            return redirect('login')

        tipo_accion = request.POST.get('tipo_accion', '')

        # 1. Enviar propuesta de oferta (solo permitido para COMPRADOR)
        if tipo_accion == 'enviar_oferta':
            perfil_usr = obtener_o_crear_perfil(request.user)
            if perfil_usr.rol != 'COMPRADOR':
                messages.warning(request, "Solo las cuentas de Comprador pueden enviar ofertas de compra.")
                return redirect('detalle_producto', producto_id=producto.id)

            if not producto.esta_publicado():
                messages.error(request, "Esta publicación ya no está disponible para recibir ofertas.")
                return redirect('detalle_producto', producto_id=producto.id)

            oferta_form = OfertaNegociacionForm(request.POST)
            if oferta_form.is_valid():
                propuesta = oferta_form.save(commit=False)
                propuesta.producto = producto
                propuesta.comprador = request.user
                propuesta.save()
                messages.success(
                    request,
                    f"Oferta enviada al vendedor: S/ {propuesta.precio_unitario_ofrecido} por {propuesta.cantidad} unidades."
                )
                return redirect('ventas_por_oferta')

        # 2. Publicar resena o comentario del producto
        elif tipo_accion == 'publicar_resena':
            resena_form = ResenaForm(request.POST)
            if resena_form.is_valid():
                nueva_resena = resena_form.save(commit=False)
                nueva_resena.producto = producto
                nueva_resena.autor = request.user
                nueva_resena.save()
                messages.success(request, "¡Gracias! Tu calificación fue agregada a la descripción del producto.")
                return redirect('detalle_producto', producto_id=producto.id)

    contexto = {
        'producto': producto,
        'relacionados': relacionados,
        'resenas': resenas,
        'oferta_form': oferta_form,
        'resena_form': resena_form,
    }
    return render(request, 'detalle_producto.html', contexto)


@login_required
def responder_oferta(request, oferta_id):
    """Permite al vendedor aceptar o rechazar una oferta de compra, o al comprador llevarla al carrito."""
    oferta = get_object_or_404(OfertaNegociacion, id=oferta_id)
    if request.method == 'POST':
        decision = request.POST.get('decision')
        respuesta = request.POST.get('respuesta_vendedor', '').strip()

        # Accion del vendedor dueno del producto
        if oferta.producto.productor == request.user:
            if decision == 'ACEPTAR':
                oferta.estado = 'ACEPTADA'
                oferta.respuesta_vendedor = respuesta or "Oferta aceptada. Puedes proceder al pago."
                oferta.save()
                messages.success(request, f"Aceptaste la oferta #{oferta.id} de {oferta.comprador.username}.")
            elif decision == 'RECHAZAR':
                oferta.estado = 'RECHAZADA'
                oferta.respuesta_vendedor = respuesta or "No es posible aceptar ese precio por el momento."
                oferta.save()
                messages.info(request, f"Rechazaste la oferta #{oferta.id}.")
            return redirect('ventas_por_oferta')

        # Accion del comprador para pagar una oferta ya aceptada
        if oferta.comprador == request.user and oferta.estado == 'ACEPTADA' and decision == 'PAGAR_OFERTA':
            ItemCarrito.objects.create(
                comprador=request.user,
                producto=oferta.producto,
                cantidad=oferta.cantidad,
                precio_unitario_acordado=oferta.precio_unitario_ofrecido
            )
            oferta.estado = 'PAGADA'
            oferta.save()
            messages.success(request, "Tu oferta aceptada fue cargada con el precio especial. Completa el pago en la pasarela.")
            return redirect('pasarela_pago')

    return redirect('ventas_por_oferta')


@login_required
def agregar_al_carrito(request, producto_id):
    perfil = obtener_o_crear_perfil(request.user)
    if perfil.rol != 'COMPRADOR':
        messages.warning(request, "Estás en una cuenta de Vendedor. Cambia a cuenta de Comprador para realizar compras.")
        return redirect('detalle_producto', producto_id=producto_id)

    producto = get_object_or_404(Producto, id=producto_id)
    if not producto.esta_publicado():
        messages.error(request, f"La publicación '{producto.nombre}' ya venció o no está disponible.")
        return redirect('detalle_producto', producto_id=producto.id)
    try:
        cantidad = int(request.POST.get('cantidad', producto.minimo_compra or 1))
    except ValueError:
        cantidad = producto.minimo_compra or 1
    if cantidad < 1:
        cantidad = 1
    if cantidad > producto.stock:
        messages.error(request, f"Solo hay {producto.stock} unidades disponibles en stock.")
        return redirect('detalle_producto', producto_id=producto.id)

    item, creado = ItemCarrito.objects.get_or_create(
        comprador=request.user,
        producto=producto,
        precio_unitario_acordado=None,
        defaults={'cantidad': cantidad}
    )
    if not creado:
        item.cantidad = min(producto.stock, item.cantidad + cantidad)
        item.save()

    ir_a_pagar = request.POST.get('comprar_ahora') == '1'
    if ir_a_pagar:
        return redirect('pasarela_pago')

    messages.success(request, f"Se agregaron {cantidad} unidades de '{producto.nombre}' a tu carrito.")
    return redirect('carrito')


@login_required
def carrito_vista(request):
    perfil = obtener_o_crear_perfil(request.user)
    if perfil.rol != 'COMPRADOR':
        messages.warning(request, "El carrito de compras es exclusivo para cuentas de Comprador.")
        return redirect('panel_productor')

    items = ItemCarrito.objects.filter(comprador=request.user).select_related('producto', 'producto__productor')
    subtotal = sum(i.subtotal() for i in items)
    costo_logistica = Decimal("15.00") if subtotal > 0 else Decimal("0.00")
    total_pagar = subtotal + costo_logistica

    contexto = {
        'items': items,
        'subtotal': subtotal,
        'costo_logistica': costo_logistica,
        'total_pagar': total_pagar,
    }
    return render(request, 'carrito.html', contexto)


@login_required
def actualizar_cantidad_carrito(request, item_id):
    """Permite al comprador cambiar la cantidad a comprar directamente desde el carrito."""
    item = get_object_or_404(ItemCarrito, id=item_id, comprador=request.user)
    if request.method == 'POST':
        try:
            nueva_cantidad = int(request.POST.get('cantidad', item.cantidad))
        except (TypeError, ValueError):
            nueva_cantidad = item.cantidad

        if nueva_cantidad < 1:
            nueva_cantidad = 1
        if nueva_cantidad > item.producto.stock:
            nueva_cantidad = item.producto.stock
            messages.warning(
                request,
                f"Se ajustó la cantidad al stock máximo disponible ({item.producto.stock} {item.producto.nombre_unidad_stock()})."
            )
        else:
            messages.success(
                request,
                f"Cantidad actualizada: {nueva_cantidad} {item.producto.nombre_unidad_stock()} de '{item.producto.nombre}'."
            )

        item.cantidad = nueva_cantidad
        item.save()
    return redirect('carrito')


@login_required
def eliminar_del_carrito(request, item_id):
    item = get_object_or_404(ItemCarrito, id=item_id, comprador=request.user)
    if request.method == 'POST':
        item.delete()
        messages.info(request, "Producto retirado del carrito.")
    return redirect('carrito')


@login_required
def pasarela_pago(request):
    """Apartado de Pasarela de Pago con Culqi vinculado al Gmail del comprador."""
    perfil = obtener_o_crear_perfil(request.user)
    if perfil.rol != 'COMPRADOR':
        messages.warning(request, "La pasarela de pago es exclusiva para cuentas de Comprador.")
        return redirect('panel_productor')

    items = ItemCarrito.objects.filter(comprador=request.user).select_related('producto', 'producto__productor')
    # Quitar del carrito lo que vencio o se pauso mientras estaba guardado
    no_disponibles = [i for i in items if not i.producto.esta_publicado()]
    if no_disponibles:
        nombres = ", ".join(i.producto.nombre for i in no_disponibles)
        ItemCarrito.objects.filter(id__in=[i.id for i in no_disponibles]).delete()
        messages.warning(request, f"Quitamos de tu carrito productos que ya no están disponibles: {nombres}.")
        items = ItemCarrito.objects.filter(comprador=request.user).select_related('producto', 'producto__productor')
    if not items.exists():
        messages.warning(request, "Tu carrito está vacío. Agrega productos antes de ir a pagar.")
        return redirect('catalogo')

    subtotal = sum(i.subtotal() for i in items)
    costo_logistica = Decimal("15.00")
    total_pagar = subtotal + costo_logistica
    correo_gmail_usuario = request.user.email or f"{request.user.username}@gmail.com"

    if request.method == 'POST':
        form = PasarelaPagoForm(request.POST)
        if form.is_valid():
            import os
            metodo = form.cleaned_data['metodo_pago']
            correo_culqi = request.POST.get('correo_culqi', '').strip() or correo_gmail_usuario
            culqi_token = request.POST.get('culqi_token', '').strip()
            clave_app_ingresada = request.POST.get('clave_app_gmail', '').strip().replace(' ', '')

            # Si el usuario ingreso su Contrasena de Aplicacion de Gmail (16 letras), la guardamos segura en .env
            if clave_app_ingresada:
                os.environ['EMAIL_HOST_USER'] = correo_culqi
                os.environ['EMAIL_HOST_PASSWORD'] = clave_app_ingresada
                settings.EMAIL_HOST_USER = correo_culqi
                settings.EMAIL_HOST_PASSWORD = clave_app_ingresada
                env_path = settings.BASE_DIR / '.env'
                lineas_actuales = {}
                if env_path.exists():
                    for lin in env_path.read_text(encoding='utf-8').splitlines():
                        if '=' in lin and not lin.strip().startswith('#'):
                            k, v = lin.split('=', 1)
                            lineas_actuales[k.strip()] = v.strip()
                lineas_actuales['EMAIL_HOST_USER'] = correo_culqi
                lineas_actuales['EMAIL_HOST_PASSWORD'] = clave_app_ingresada
                env_path.write_text("\n".join([f"{k}={v}" for k, v in lineas_actuales.items()]) + "\n", encoding='utf-8')

            # Actualizar el Gmail en el usuario si estaba vacio
            if correo_culqi and request.user.email != correo_culqi:
                request.user.email = correo_culqi
                request.user.save()

            if metodo == 'TARJETA':
                exito_culqi, codigo_tx, mensaje_culqi = procesar_cobro_culqi(
                    total_pagar, correo_culqi, culqi_token
                )
                if not exito_culqi:
                    messages.error(request, f"Error en Pasarela Culqi: {mensaje_culqi}")
                    return redirect('pasarela_pago')
                estado_pago = 'PAGADO'
            else:
                codigo_tx = f"AGRO-2026-{uuid.uuid4().hex[:6].upper()}"
                estado_pago = 'PENDIENTE_VERIFICACION' if metodo == 'CONTRAENTREGA' else 'PAGADO'

            pedidos_creados = []
            for item in items:
                prod = item.producto
                cant = min(item.cantidad, prod.stock) if prod.stock > 0 else item.cantidad
                precio_unit = item.precio_aplicado()
                ped = Pedido.objects.create(
                    comprador=request.user,
                    producto=prod,
                    cantidad=cant,
                    precio_unitario=precio_unit,
                    total=cant * precio_unit,
                    direccion_entrega=form.cleaned_data['direccion_entrega'],
                    ciudad_destino=form.cleaned_data['ciudad_destino'],
                    telefono_contacto=form.cleaned_data['telefono_contacto'],
                    comentario=form.cleaned_data['comentario'],
                    metodo_pago=metodo,
                    estado_pago=estado_pago,
                    codigo_transaccion=codigo_tx,
                    estado='CONFIRMADO',
                )
                pedidos_creados.append(ped)
                if prod.stock >= cant:
                    prod.stock -= cant
                    if prod.stock == 0:
                        prod.disponible = False
                    prod.save()

            items.delete()

            # Enviar comprobante al correo Gmail del comprador
            enviado_ok = enviar_comprobante_gmail(
                request.user,
                correo_culqi,
                codigo_tx,
                pedidos_creados,
                total_pagar,
                dict(Pedido.METODOS_PAGO).get(metodo, metodo)
            )

            if enviado_ok:
                messages.success(
                    request,
                    f"¡Pago procesado con Culqi ({codigo_tx})! La boleta fue enviada a tu bandeja de Gmail ({correo_culqi})."
                )
            else:
                messages.success(
                    request,
                    f"¡Pago procesado con Culqi ({codigo_tx})! Para que llegue el correo a tu bandeja de Gmail, agrega tu Contraseña de Aplicación de 16 letras."
                )
            return redirect('comprobante_pago', codigo=codigo_tx)
    else:
        form = PasarelaPagoForm(initial={
            'ciudad_destino': perfil.ubicacion if perfil.ubicacion in LUGARES_AREQUIPA else LUGAR_POR_DEFECTO,
            'telefono_contacto': perfil.telefono or '999445566',
            'metodo_pago': 'TARJETA',
        })

    import os
    tiene_smtp_gmail = bool((os.environ.get('EMAIL_HOST_PASSWORD') or getattr(settings, 'EMAIL_HOST_PASSWORD', '')).strip())
    algun_vendedor_tiene_cuenta = any(
        bool((obtener_o_crear_perfil(i.producto.productor).cuenta_bancaria or '').strip())
        for i in items
    )
    contexto = {
        'items': items,
        'subtotal': subtotal,
        'costo_logistica': costo_logistica,
        'total_pagar': total_pagar,
        'total_centimos': int(total_pagar * 100),
        'correo_gmail_usuario': correo_gmail_usuario,
        'tiene_smtp_gmail': tiene_smtp_gmail,
        'algun_vendedor_tiene_cuenta': algun_vendedor_tiene_cuenta,
        'culqi_public_key': getattr(settings, 'CULQI_PUBLIC_KEY', 'pk_test_0000000000000000'),
        'form': form,
    }
    return render(request, 'pasarela_pago.html', contexto)


@login_required
def comprobante_pago(request, codigo):
    """Muestra la boleta / comprobante electronico formal generado tras pasar por la pasarela de pago."""
    pedidos_tx = Pedido.objects.filter(comprador=request.user, codigo_transaccion=codigo).select_related('producto', 'producto__productor')
    if not pedidos_tx.exists():
        return redirect('mis_pedidos')

    primer_pedido = pedidos_tx.first()
    serie_boleta = f"B001-{primer_pedido.id:06d}" if primer_pedido else "B001-000001"
    subtotal_tx = sum(p.total for p in pedidos_tx)
    costo_logistica = Decimal("15.00")
    total_tx = subtotal_tx + costo_logistica

    contexto = {
        'codigo': codigo,
        'serie_boleta': serie_boleta,
        'pedidos_tx': pedidos_tx,
        'primer_pedido': primer_pedido,
        'subtotal_tx': subtotal_tx,
        'costo_logistica': costo_logistica,
        'total_tx': total_tx,
    }
    return render(request, 'comprobante_pago.html', contexto)


def lista_productores(request):
    asegurar_datos_iniciales()
    perfiles_productores = PerfilUsuario.objects.filter(rol='PRODUCTOR').select_related('usuario')
    return render(request, 'productores.html', {'perfiles_productores': perfiles_productores})


def registro_vista(request):
    if request.user.is_authenticated:
        return redirect('inicio')

    rol_inicial = request.GET.get('rol', 'COMPRADOR')
    if rol_inicial not in ['COMPRADOR', 'PRODUCTOR']:
        rol_inicial = 'COMPRADOR'

    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            PerfilUsuario.objects.create(
                usuario=usuario,
                rol=form.cleaned_data['rol'],
                ruc_dni=form.cleaned_data.get('ruc_dni', ''),
                telefono=form.cleaned_data.get('telefono', ''),
                ubicacion=form.cleaned_data.get('ubicacion', ''),
                nombre_finca=form.cleaned_data.get('nombre_finca', ''),
                cuenta_bancaria=form.cleaned_data.get('cuenta_bancaria', '') if form.cleaned_data['rol'] == 'PRODUCTOR' else '',
            )
            login(request, usuario)
            messages.success(request, f"¡Bienvenido(a), {usuario.first_name}! Cuenta creada con contraseña encriptada.")
            # Lo primero que ve el usuario nuevo son las ofertas vigentes
            return redirect('ventas_por_oferta')
    else:
        form = RegistroUsuarioForm(initial={'rol': rol_inicial})

    return render(request, 'registro.html', {'form': form, 'rol_inicial': rol_inicial})


def login_vista(request):
    """Apartado de Login que permite ingresar con usuario o con correo Gmail y contrasena encriptada."""
    asegurar_datos_iniciales()
    if request.user.is_authenticated:
        return redirect('inicio')

    modo_acceso = request.GET.get('modo', 'comprador')

    if request.method == 'POST':
        identificador = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        modo_elegido = request.POST.get('modo_rol', '')

        # Permitir iniciar sesion escribiendo directamente el correo Gmail o el nombre de usuario
        username_real = identificador
        if '@' in identificador:
            usr_por_correo = User.objects.filter(email__iexact=identificador).first()
            if usr_por_correo:
                username_real = usr_por_correo.username

        usuario = authenticate(request, username=username_real, password=password)
        if usuario is not None:
            perfil = obtener_o_crear_perfil(usuario)
            if modo_elegido in ['PRODUCTOR', 'COMPRADOR'] and perfil.rol != modo_elegido:
                rol_nombre = "Vendedor" if modo_elegido == 'PRODUCTOR' else "Comprador"
                messages.error(request, f"La cuenta '{identificador}' no pertenece al perfil de {rol_nombre}. Usa la pestaña correspondiente.")
                return render(request, 'login.html', {
                    'modo_acceso': 'vendedor' if modo_elegido == 'PRODUCTOR' else 'comprador',
                    'google_client_id': getattr(settings, 'GOOGLE_CLIENT_ID', ''),
                })

            login(request, usuario)
            messages.success(request, f"Sesión iniciada con {usuario.email or usuario.username} ({perfil.get_rol_display()}).")
            siguiente = request.POST.get('next') or request.GET.get('next', '')
            if siguiente and url_has_allowed_host_and_scheme(siguiente, allowed_hosts={request.get_host()}):
                return redirect(siguiente)
            return redirect('ventas_por_oferta')
        else:
            messages.error(request, "Correo/usuario o contraseña incorrectos. Verifica tus datos.")

    return render(request, 'login.html', {
        'modo_acceso': modo_acceso,
        'google_client_id': getattr(settings, 'GOOGLE_CLIENT_ID', ''),
    })


def login_google(request):
    """
    Redirige directamente a la ventana oficial de Google OAuth 2.0
    (https://accounts.google.com/o/oauth2/v2/auth) con prompt=select_account
    para que el usuario seleccione su correo Gmail autentico.
    """
    import os
    asegurar_datos_iniciales()

    rol_elegido = request.GET.get('rol') or request.POST.get('modo_rol', 'COMPRADOR')
    if rol_elegido not in ['COMPRADOR', 'PRODUCTOR']:
        rol_elegido = 'COMPRADOR'
    request.session['rol_google_pendiente'] = rol_elegido

    # Si el usuario pega su Client ID y Client Secret desde la pantalla de configuracion rapida, se guarda en .env
    if request.method == 'POST' and request.POST.get('guardar_credenciales_google') == '1':
        nuevo_id = request.POST.get('google_client_id', '').strip()
        nuevo_secret = request.POST.get('google_client_secret', '').strip()
        if nuevo_id and nuevo_secret:
            os.environ['GOOGLE_CLIENT_ID'] = nuevo_id
            os.environ['GOOGLE_CLIENT_SECRET'] = nuevo_secret
            settings.GOOGLE_CLIENT_ID = nuevo_id
            settings.GOOGLE_CLIENT_SECRET = nuevo_secret

            env_path = settings.BASE_DIR / '.env'
            lineas_actuales = {}
            if env_path.exists():
                for lin in env_path.read_text(encoding='utf-8').splitlines():
                    if '=' in lin and not lin.strip().startswith('#'):
                        k, v = lin.split('=', 1)
                        lineas_actuales[k.strip()] = v.strip()
            lineas_actuales['GOOGLE_CLIENT_ID'] = nuevo_id
            lineas_actuales['GOOGLE_CLIENT_SECRET'] = nuevo_secret
            contenido_env = "\n".join([f"{k}={v}" for k, v in lineas_actuales.items()]) + "\n"
            env_path.write_text(contenido_env, encoding='utf-8')

    client_id = (os.environ.get('GOOGLE_CLIENT_ID') or getattr(settings, 'GOOGLE_CLIENT_ID', '')).strip()
    redirect_uri = request.build_absolute_uri('/login/google/callback/')

    if not client_id:
        messages.warning(
            request,
            f"Para abrir el selector oficial de Google, pega tu GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET de Google Cloud (URI de redirección: {redirect_uri})."
        )
        return render(request, 'login.html', {
            'modo_acceso': 'vendedor' if rol_elegido == 'PRODUCTOR' else 'comprador',
            'mostrar_config_google': True,
            'redirect_uri_google': redirect_uri,
        })

    parametros = urllib.parse.urlencode({
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'access_type': 'online',
        'prompt': 'select_account',
        'state': rol_elegido,
    })
    return redirect(f"https://accounts.google.com/o/oauth2/v2/auth?{parametros}")


def login_google_callback(request):
    """
    Recibe la respuesta oficial de Google OAuth 2.0 tras seleccionar el Gmail autentico,
    obtiene los datos reales del usuario desde googleapis.com y lo autentica en Django.
    """
    import os
    asegurar_datos_iniciales()

    error_google = request.GET.get('error')
    if error_google:
        messages.error(request, f"Inicio con Google cancelado: {error_google}")
        return redirect('login')

    code = request.GET.get('code', '').strip()
    rol_elegido = request.GET.get('state') or request.session.get('rol_google_pendiente', 'COMPRADOR')
    if rol_elegido not in ['COMPRADOR', 'PRODUCTOR']:
        rol_elegido = 'COMPRADOR'

    if not code:
        return redirect('login')

    client_id = (os.environ.get('GOOGLE_CLIENT_ID') or getattr(settings, 'GOOGLE_CLIENT_ID', '')).strip()
    client_secret = (os.environ.get('GOOGLE_CLIENT_SECRET') or getattr(settings, 'GOOGLE_CLIENT_SECRET', '')).strip()
    redirect_uri = request.build_absolute_uri('/login/google/callback/')

    try:
        datos_post = urllib.parse.urlencode({
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        }).encode('utf-8')

        req_token = urllib.request.Request(
            'https://oauth2.googleapis.com/token',
            data=datos_post,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            method='POST'
        )
        with urllib.request.urlopen(req_token, timeout=10) as resp_token:
            token_json = json.loads(resp_token.read().decode('utf-8'))

        access_token = token_json.get('access_token')
        req_userinfo = urllib.request.Request(
            'https://www.googleapis.com/oauth2/v3/userinfo',
            headers={'Authorization': f'Bearer {access_token}'},
            method='GET'
        )
        with urllib.request.urlopen(req_userinfo, timeout=10) as resp_user:
            info_google = json.loads(resp_user.read().decode('utf-8'))

        email_google = info_google.get('email', '').strip().lower()
        nombre_google = info_google.get('given_name', '')
        apellido_google = info_google.get('family_name', '')
    except Exception as e:
        messages.error(request, f"Error al validar tu cuenta con Google OAuth: {e}")
        return redirect('login')

    if not email_google:
        messages.error(request, "Google no devolvió una dirección de correo electrónico.")
        return redirect('login')

    usuario = User.objects.filter(email__iexact=email_google).first()
    if not usuario:
        base_username = email_google.split('@')[0][:20]
        username_final = base_username
        contador = 1
        while User.objects.filter(username=username_final).exists():
            username_final = f"{base_username}{contador}"
            contador += 1

        usuario = User(
            username=username_final,
            email=email_google,
            first_name=nombre_google or base_username.capitalize(),
            last_name=apellido_google,
        )
        usuario.set_unusable_password()
        usuario.save()

        PerfilUsuario.objects.create(
            usuario=usuario,
            rol=rol_elegido,
            ubicacion=LUGAR_POR_DEFECTO,
            telefono="",
        )
    else:
        if nombre_google and not usuario.first_name:
            usuario.first_name = nombre_google
            usuario.last_name = apellido_google
            usuario.save()
        perfil = obtener_o_crear_perfil(usuario)
        perfil.rol = rol_elegido
        perfil.save()

    login(request, usuario)
    messages.success(request, f"¡Bienvenido(a), {usuario.first_name}! Ingresaste con tu cuenta oficial de Google ({usuario.email}).")
    return redirect('ventas_por_oferta')


@login_required
def cambiar_modo_vista(request):
    """
    Si el usuario entro con su propia cuenta de Google, cambia su propio perfil entre
    Vendedor (PRODUCTOR) y Comprador (COMPRADOR) conservando su mismo Gmail.
    """
    asegurar_datos_iniciales()
    if request.method == 'POST':
        nuevo_rol = request.POST.get('nuevo_rol')
        if nuevo_rol in ['PRODUCTOR', 'COMPRADOR']:
            # Si usa las cuentas de demostracion clasicas, alterna entre ellas
            if request.user.username in ['productor_mantaro', 'comprador_lima']:
                target_user = 'productor_mantaro' if nuevo_rol == 'PRODUCTOR' else 'comprador_lima'
                u_demo = User.objects.filter(username=target_user).first()
                if u_demo:
                    login(request, u_demo)
                    if nuevo_rol == 'PRODUCTOR':
                        return redirect('panel_productor')
                    return redirect('panel_comprador')
            else:
                # Si entro con su cuenta de Google autentica, mantiene su mismo correo y cambia su vista/rol
                perfil = obtener_o_crear_perfil(request.user)
                perfil.rol = nuevo_rol
                perfil.save()
                nombre_modo = "Vendedor / Productor" if nuevo_rol == 'PRODUCTOR' else "Comprador"
                messages.info(request, f"Cambiaste tu vista a {nombre_modo} con tu cuenta ({request.user.email}).")
                if nuevo_rol == 'PRODUCTOR':
                    return redirect('panel_productor')
                return redirect('panel_comprador')
    return redirect('inicio')


def logout_vista(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('inicio')


@login_required
def panel_comprador(request):
    """Apartado visual exclusivo para el Comprador."""
    perfil = obtener_o_crear_perfil(request.user)
    if perfil.rol != 'COMPRADOR':
        messages.warning(request, "Esa sección es exclusiva para Compradores. Te redirigimos a tu Panel de Vendedor.")
        return redirect('panel_productor')

    compras_recientes = Pedido.objects.filter(comprador=request.user).select_related('producto', 'producto__productor')[:5]
    mis_ofertas = OfertaNegociacion.objects.filter(comprador=request.user).select_related('producto')[:5]
    items_carrito = ItemCarrito.objects.filter(comprador=request.user).select_related('producto')
    productos_recomendados = Producto.objects.ofertas_activas()[:3]

    total_invertido = sum(c.total for c in Pedido.objects.filter(comprador=request.user).exclude(estado='CANCELADO'))

    contexto = {
        'perfil': perfil,
        'compras_recientes': compras_recientes,
        'mis_ofertas': mis_ofertas,
        'items_carrito': items_carrito,
        'productos_recomendados': productos_recomendados,
        'total_invertido': total_invertido,
    }
    return render(request, 'panel_comprador.html', contexto)


@login_required
def panel_productor(request):
    """Apartado visual exclusivo para el Vendedor / Productor Agricola."""
    perfil = obtener_o_crear_perfil(request.user)
    if perfil.rol != 'PRODUCTOR':
        messages.warning(request, "El Panel de Vendedor es exclusivo para Productores Agrícolas.")
        return redirect('panel_comprador')

    mis_productos = Producto.objects.filter(productor=request.user)
    pedidos_recibidos = Pedido.objects.filter(producto__productor=request.user).select_related('comprador', 'producto')
    ofertas_recibidas = OfertaNegociacion.objects.filter(producto__productor=request.user).select_related('comprador', 'producto')

    ingresos_estimados = sum(
        p.total for p in pedidos_recibidos if p.estado in ['CONFIRMADO', 'EN_CAMINO', 'ENTREGADO']
    )

    contexto = {
        'perfil': perfil,
        'mis_productos': mis_productos,
        'total_activos': mis_productos.publicados().count(),
        'total_ofertas_activas': mis_productos.ofertas_activas().count(),
        'total_vencidas': mis_productos.filter(fecha_vencimiento__lte=timezone.now()).count(),
        'pedidos_recibidos': pedidos_recibidos,
        'ofertas_recibidas': ofertas_recibidas,
        'ingresos_estimados': ingresos_estimados,
        'estados_pedido': Pedido.ESTADOS,
    }
    return render(request, 'panel_productor.html', contexto)


@login_required
def crear_producto(request):
    perfil = obtener_o_crear_perfil(request.user)
    if perfil.rol != 'PRODUCTOR':
        messages.error(request, "Solo los Vendedores / Productores pueden publicar productos.")
        return redirect('panel_comprador')

    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.productor = request.user
            if producto.en_oferta:
                # Si se publica como oferta, queda oculto hasta pagar la comision
                producto.oferta_pendiente_pago = True
                producto.disponible = False
                producto.save()
                messages.info(request, "Para publicar tu producto como oferta primero debes pagar la comisión de AgroComercial.")
                return redirect('pagar_comision_oferta', producto_id=producto.id)
            producto.save()
            messages.success(request, f"El producto '{producto.nombre}' fue publicado exitosamente.")
            return redirect('panel_productor')
    else:
        form = ProductoForm()

    return render(request, 'form_producto.html', {
        'form': form,
        'accion': 'Publicar Nuevo Producto',
        'comision_porcentaje': settings.COMISION_OFERTA_PORCENTAJE,
        'comision_minima': settings.COMISION_OFERTA_MINIMA,
    })


@login_required
def editar_producto(request, producto_id):
    perfil = obtener_o_crear_perfil(request.user)
    if perfil.rol != 'PRODUCTOR':
        messages.error(request, "Un Comprador no puede editar productos.")
        return redirect('panel_comprador')

    producto = get_object_or_404(Producto, id=producto_id, productor=request.user)
    # Solo se cobra de nuevo si la oferta anterior ya termino o nunca se pago
    estaba_en_oferta = (
        producto.en_oferta and not producto.oferta_pendiente_pago
        and (producto.oferta_fin is None or producto.oferta_fin > timezone.now())
    )
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            producto = form.save(commit=False)
            if producto.en_oferta and not estaba_en_oferta:
                # Pasar un producto a oferta tambien cobra la comision antes de publicarse
                producto.oferta_pendiente_pago = True
                producto.disponible = False
                producto.save()
                messages.info(request, "Para publicar tu producto como oferta primero debes pagar la comisión de AgroComercial.")
                return redirect('pagar_comision_oferta', producto_id=producto.id)
            producto.oferta_pendiente_pago = False
            producto.save()
            messages.success(request, f"El producto '{producto.nombre}' fue actualizado.")
            return redirect('panel_productor')
    else:
        form = ProductoForm(instance=producto)

    return render(request, 'form_producto.html', {
        'form': form,
        'producto': producto,
        'accion': 'Editar mi Producto Agrícola',
        'comision_porcentaje': settings.COMISION_OFERTA_PORCENTAJE,
        'comision_minima': settings.COMISION_OFERTA_MINIMA,
    })


@login_required
def pagar_comision_oferta(request, producto_id):
    """Apartado de pago (simulado) de la comision por publicar un producto en oferta."""
    producto = get_object_or_404(Producto, id=producto_id, productor=request.user)
    if not producto.oferta_pendiente_pago:
        messages.info(request, f"El producto '{producto.nombre}' no tiene comisiones pendientes.")
        return redirect('panel_productor')

    monto = producto.monto_comision_oferta()
    if request.method == 'POST':
        metodo = request.POST.get('metodo_pago', 'YAPE_PLIN')
        if metodo not in dict(PagoComision.METODOS):
            metodo = 'YAPE_PLIN'
        # Pago simulado: no se cobra dinero real, solo se registra la operacion
        pago = PagoComision.objects.create(
            producto=producto,
            productor=request.user,
            porcentaje=Decimal(str(settings.COMISION_OFERTA_PORCENTAJE)),
            monto=monto,
            metodo_pago=metodo,
            codigo_transaccion=f"COM-{uuid.uuid4().hex[:10].upper()}",
        )
        producto.oferta_pendiente_pago = False
        producto.disponible = True
        producto.save()
        messages.success(request, f"Pago de comisión S/ {pago.monto} recibido (código {pago.codigo_transaccion}). ¡Tu oferta '{producto.nombre}' ya está publicada!")
        return redirect('detalle_producto', producto_id=producto.id)

    contexto = {
        'producto': producto,
        'monto': monto,
        'porcentaje': settings.COMISION_OFERTA_PORCENTAJE,
        'minimo': settings.COMISION_OFERTA_MINIMA,
    }
    return render(request, 'pagar_comision.html', contexto)


@login_required
def eliminar_producto(request, producto_id):
    perfil = obtener_o_crear_perfil(request.user)
    if perfil.rol != 'PRODUCTOR':
        messages.error(request, "Acción no permitida para Compradores.")
        return redirect('panel_comprador')

    producto = get_object_or_404(Producto, id=producto_id, productor=request.user)
    if request.method == 'POST':
        nombre = producto.nombre
        producto.delete()
        messages.info(request, f"El producto '{nombre}' fue eliminado.")
    return redirect('panel_productor')


@login_required
def renovar_producto(request, producto_id):
    """Vuelve a publicar un producto por PUBLICACION_DIAS_VIGENCIA dias desde hoy."""
    producto = get_object_or_404(Producto, id=producto_id, productor=request.user)
    if request.method == 'POST':
        dias = settings.PUBLICACION_DIAS_VIGENCIA
        producto.fecha_vencimiento = timezone.now() + timedelta(days=dias)
        producto.save(update_fields=['fecha_vencimiento'])
        messages.success(request, f"'{producto.nombre}' quedó publicado {dias} días más.")
    return redirect('panel_productor')


@login_required
def pausar_producto(request, producto_id):
    """Pausa o vuelve a activar una publicacion sin borrarla."""
    producto = get_object_or_404(Producto, id=producto_id, productor=request.user)
    if request.method == 'POST':
        if producto.oferta_pendiente_pago:
            messages.warning(request, "Primero paga la comisión de la oferta para poder activarla.")
            return redirect('pagar_comision_oferta', producto_id=producto.id)
        producto.disponible = not producto.disponible
        producto.save(update_fields=['disponible'])
        estado = "activada" if producto.disponible else "pausada"
        messages.info(request, f"La publicación '{producto.nombre}' fue {estado}.")
    return redirect('panel_productor')


@login_required
def cambiar_estado_pedido(request, pedido_id):
    perfil = obtener_o_crear_perfil(request.user)
    pedido = get_object_or_404(Pedido, id=pedido_id)
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        estados_validos = dict(Pedido.ESTADOS).keys()

        if perfil.rol == 'PRODUCTOR' and pedido.producto.productor == request.user and nuevo_estado in estados_validos:
            pedido.estado = nuevo_estado
            pedido.save()
            messages.success(request, f"Estado del pedido #{pedido.id} actualizado a '{pedido.get_estado_display()}'.")
            return redirect('panel_productor')

        if perfil.rol == 'COMPRADOR' and pedido.comprador == request.user and pedido.estado in ['PENDIENTE', 'CONFIRMADO'] and nuevo_estado == 'CANCELADO':
            pedido.estado = 'CANCELADO'
            pedido.estado_pago = 'REEMBOLSADO'
            pedido.save()
            pedido.producto.stock += pedido.cantidad
            pedido.producto.disponible = True
            pedido.producto.save()
            messages.info(request, f"El pedido #{pedido.id} fue cancelado y el stock fue repuesto.")
            return redirect('mis_pedidos')

    return redirect('inicio')


@login_required
def mis_pedidos(request):
    perfil = obtener_o_crear_perfil(request.user)
    if perfil.rol != 'COMPRADOR':
        return redirect('panel_productor')

    compras = Pedido.objects.filter(comprador=request.user).select_related('producto', 'producto__productor')
    total_gastado = sum(c.total for c in compras if c.estado != 'CANCELADO')
    return render(request, 'mis_pedidos.html', {
        'compras': compras,
        'total_gastado': total_gastado,
    })


@login_required
def perfil_vista(request):
    perfil = obtener_o_crear_perfil(request.user)
    if request.method == 'POST':
        form = PerfilForm(request.POST, instance=perfil)
        if form.is_valid():
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.email = form.cleaned_data['email']
            request.user.save()
            form.save()
            messages.success(request, "Tus datos de perfil fueron actualizados correctamente.")
            return redirect('perfil')
    else:
        form = PerfilForm(instance=perfil, initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
        })

    return render(request, 'perfil.html', {'form': form, 'perfil': perfil})
