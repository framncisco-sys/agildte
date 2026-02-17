"""
Generador de PDF - Versión Legible según Modelo MH El Salvador.
Usa ReportLab Platypus (Paragraph + Table) para que el texto respete márgenes y no se desborde.
QR generado con qrcode y dibujado vía ImageReader.
"""
import io
import xml.sax.saxutils as saxutils
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

try:
    from num2words import num2words
except ImportError:
    num2words = None

# QR: importar qrcode (con PIL) para generar PNG en memoria
try:
    import qrcode
except ImportError:
    qrcode = None


MARGIN = 1.5 * cm
PAGE_W, PAGE_H = letter
LEFT = MARGIN
RIGHT = PAGE_W - MARGIN
TOP = PAGE_H - MARGIN
BOTTOM = MARGIN

# Ancho útil para párrafos (evitar desborde)
ANCHO_PARRAFO_EMISOR = 7 * cm
ANCHO_PARRAFO_RECEPTOR = 7 * cm


def _escape_html(text):
    """Escapa caracteres para usar dentro de un Paragraph (evitar romper HTML)."""
    if not text:
        return ""
    return saxutils.escape(str(text).strip())


def _formatear_fecha_hora(venta):
    """Formato DD/MM/YYYY HH:MM:SS para PDF."""
    if not venta.fecha_emision:
        return ''
    fecha = venta.fecha_emision.strftime('%d/%m/%Y')
    hora = (venta.hora_emision or '').strip()
    if hora and len(hora) >= 8:
        return f"{fecha} {hora[:8]}"
    if hora and len(hora) >= 5:
        return f"{fecha} {hora[:5]}"
    return fecha


def _valor_en_letras(total_pagar):
    """Convierte el total a valor en letras (ej: CIEN DÓLARES CON 00/100 USD)."""
    try:
        total = float(Decimal(str(total_pagar)))
    except (TypeError, ValueError):
        return "CERO DÓLARES CON 00/100 USD"
    entero = int(total)
    centavos = round((total - entero) * 100)
    if centavos >= 100:
        centavos = 0
        entero += 1
    centavos_str = f"{centavos:02d}"
    if num2words:
        try:
            palabras = num2words(entero, lang='es')
            palabras = palabras.upper().replace('Á', 'A').replace('É', 'E').replace('Í', 'I').replace('Ó', 'O').replace('Ú', 'U')
        except Exception:
            palabras = str(entero)
    else:
        palabras = str(entero)
    return f"{palabras} DÓLARES CON {centavos_str}/100 USD"


def _obtener_ruta_logo(empresa):
    """Obtiene la ruta del logo: empresa.logo, static/logo.png o None."""
    if empresa and getattr(empresa, 'logo', None) and empresa.logo:
        try:
            path = empresa.logo.path
            if path and Path(path).exists():
                return path
        except (ValueError, OSError):
            pass
    base_dir = getattr(settings, 'BASE_DIR', Path(__file__).resolve().parent.parent.parent)
    for candidate in [
        base_dir / 'api' / 'static' / 'logo.png',
        base_dir / 'static' / 'logo.png',
        Path(settings.STATIC_ROOT) / 'logo.png' if getattr(settings, 'STATIC_ROOT', None) else None,
    ]:
        if candidate and Path(candidate).exists():
            return str(candidate)
    return None


def _generar_qr_imagen_reportlab(url, size_pt=70):
    """
    Genera el código QR como imagen compatible con ReportLab.
    Retorna un objeto que ReportLab puede dibujar (BytesIO con PNG) o None si falla.
    """
    if not qrcode:
        return None
    try:
        qr = qrcode.QRCode(version=1, box_size=3, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        # Asegurar que usamos backend PIL para tener .resize() y .save()
        img = qr.make_image(fill_color="black", back_color="white")
        # Convertir a bytes PNG en memoria
        buf = io.BytesIO()
        if hasattr(img, 'resize'):
            size_px = max(80, int(size_pt * 2.5))
            img = img.resize((size_px, size_px))
        img.save(buf, format='PNG')
        buf.seek(0)
        return buf
    except Exception:
        return None


def _d(val, default=0):
    """Convierte a float para cálculos."""
    try:
        return float(Decimal(str(val or default)))
    except (TypeError, ValueError):
        return float(default)


def _obtener_datos_emisor(venta):
    empresa = venta.empresa
    if not empresa:
        return {
            'nombre': 'EMPRESA S.A. DE C.V.',
            'nrc': '0000-000000-000-0',
            'nit': '0614-000000-000-0',
            'direccion': 'San Salvador, El Salvador',
            'telefono': '',
            'correo': '',
        }
    return {
        'nombre': (empresa.nombre or 'EMPRESA S.A. DE C.V.').strip(),
        'nrc': (empresa.nrc or '0000-000000-000-0').strip(),
        'nit': (empresa.nit or '').strip() or '0614-000000-000-0',
        'direccion': (getattr(empresa, 'direccion', None) or '').strip() or 'San Salvador, El Salvador',
        'telefono': (getattr(empresa, 'telefono', None) or '').strip(),
        'correo': (getattr(empresa, 'correo', None) or '').strip(),
    }


def _obtener_datos_receptor(venta):
    nombre = (venta.nombre_receptor or '').strip()
    if not nombre and venta.cliente:
        nombre = (venta.cliente.nombre or '').strip()
    if not nombre:
        nombre = 'Consumidor Final'
    nrc = (venta.nrc_receptor or '').strip()
    if not nrc and venta.cliente:
        nrc = (venta.cliente.nrc or '').strip()
    nit_dui = (venta.documento_receptor or '').strip()
    if not nit_dui and venta.cliente:
        nit_dui = (venta.cliente.documento_identidad or venta.cliente.nit or venta.cliente.dui or '').strip()
    direccion = (venta.direccion_receptor or '').strip()
    if not direccion and venta.cliente:
        direccion = (getattr(venta.cliente, 'direccion', None) or '').strip()
    correo = (venta.correo_receptor or '').strip()
    if not correo and venta.cliente:
        correo = (getattr(venta.cliente, 'email_contacto', None) or '').strip()
    actividad = ''
    if venta.cliente:
        cod = (getattr(venta.cliente, 'cod_actividad', None) or '').strip()
        desc = (getattr(venta.cliente, 'desc_actividad', None) or '').strip()
        if cod or desc:
            actividad = f"{cod} - {desc}".strip(' -')
    return {
        'nombre': nombre,
        'nit_dui': nit_dui or 'N/A',
        'nrc': nrc or 'N/A',
        'actividad_economica': actividad or 'N/A',
        'direccion': direccion or 'N/A',
        'correo': correo or 'N/A',
    }


def _tipo_documento_label(venta):
    tipo = (venta.tipo_venta or 'CF').upper()
    if tipo == 'CCF':
        return 'COMPROBANTE DE CRÉDITO FISCAL'
    if tipo == 'NC':
        return 'NOTA DE CRÉDITO'
    if tipo == 'ND':
        return 'NOTA DE DÉBITO'
    return 'FACTURA'


def generar_pdf_venta(venta):
    """
    Genera el PDF de la versión legible del DTE según modelo MH.
    Todo el contenido usa Platypus (Paragraph + Table) para respetar márgenes.
    Returns: BytesIO con el contenido del PDF.
    """
    buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    estilo_normal = ParagraphStyle(
        name='NormalWrap',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        wordWrap='CJK',
    )
    estilo_bold = ParagraphStyle(
        name='BoldWrap',
        parent=estilo_normal,
        fontName='Helvetica-Bold',
    )
    # Fuente más pequeña para el Sello de Recepción (texto muy largo)
    estilo_sello = ParagraphStyle(
        name='SelloSmall',
        parent=estilo_normal,
        fontSize=6,
        leading=8,
        wordWrap='CJK',
    )

    emisor = _obtener_datos_emisor(venta)
    receptor = _obtener_datos_receptor(venta)
    fecha_hora = _formatear_fecha_hora(venta)
    codigo_gen = (venta.codigo_generacion or '').strip() or 'N/A'
    numero_control = (venta.numero_control or venta.numero_documento or '').strip() or 'N/A'
    sello = (venta.sello_recepcion or '').strip() or 'N/A'
    empresa = venta.empresa
    ambiente = getattr(empresa, 'ambiente', None) or '01'
    # Hacienda exige fecha en formato ISO 8601 (YYYY-MM-DD) para el QR
    fecha_iso = venta.fecha_emision.strftime('%Y-%m-%d') if venta.fecha_emision else ''
    url_consulta = (
        f"https://admin.factura.gob.sv/consultaPublica?"
        f"ambiente={ambiente}&codGen={codigo_gen}&fechaEmi={fecha_iso}"
    )

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )
    elements = []

    # ----- LOGO + DATOS EMISOR (Paragraph para dirección larga) -----
    logo_path = _obtener_ruta_logo(empresa) if empresa else None
    logo_w, logo_h = 100, 55
    if logo_path:
        try:
            img_logo = Image(logo_path, width=logo_w, height=logo_h)
        except Exception:
            img_logo = None
    else:
        img_logo = None

    # Emisor: Paragraph para nombre y dirección (se ajustan al ancho, máx 7cm)
    emisor_nombre_p = Paragraph(_escape_html(emisor['nombre']), estilo_bold)
    emisor_nrc_nit_p = Paragraph(
        f"NRC: {_escape_html(emisor['nrc'])} &nbsp; NIT: {_escape_html(emisor['nit'])}",
        estilo_normal,
    )
    emisor_direccion_p = Paragraph(_escape_html(emisor['direccion']), estilo_normal)
    lineas_emisor = [emisor_nombre_p, emisor_nrc_nit_p, emisor_direccion_p]
    if emisor['telefono']:
        lineas_emisor.append(Paragraph(f"Tel: {_escape_html(emisor['telefono'])}", estilo_normal))
    if emisor['correo']:
        lineas_emisor.append(Paragraph(f"Correo: {_escape_html(emisor['correo'])}", estilo_normal))
    tabla_emisor_celda = Table([[p] for p in lineas_emisor], colWidths=[ANCHO_PARRAFO_EMISOR])
    tabla_emisor_celda.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))

    # Columna izquierda: logo arriba + datos emisor
    if img_logo:
        izquierda_content = Table([[img_logo], [tabla_emisor_celda]], colWidths=[ANCHO_PARRAFO_EMISOR])
    else:
        placeholder = Paragraph('<i>LOGO</i>', estilo_normal)
        izquierda_content = Table([[placeholder], [tabla_emisor_celda]], colWidths=[ANCHO_PARRAFO_EMISOR])
    izquierda_content.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))

    # ----- Tabla anidada DTE (derecha): con bordes GRID y fondo gris en títulos -----
    datos_criticos = [
        ('Código de Generación:', Paragraph(_escape_html(codigo_gen), estilo_normal)),
        ('Número de Control:', Paragraph(_escape_html(numero_control), estilo_normal)),
        ('Sello de Recepción:', Paragraph(_escape_html(sello), estilo_sello)),
        ('Fecha y Hora de Emisión:', Paragraph(_escape_html(fecha_hora), estilo_normal)),
        ('Modelo de Facturación:', Paragraph('Previo', estilo_normal)),
        ('Tipo de Transmisión:', Paragraph('Normal', estilo_normal)),
    ]
    filas_dte = []
    for label, value_flowable in datos_criticos:
        filas_dte.append([
            Paragraph(f"<b>{_escape_html(label)}</b>", estilo_normal),
            value_flowable,
        ])
    tabla_dte = Table(filas_dte, colWidths=[95, 100])
    tabla_dte.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E5E7EB')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))

    titulo_dte = Paragraph('<b>DOCUMENTO TRIBUTARIO ELECTRÓNICO</b>', estilo_bold)
    subtitulo_dte = Paragraph(_escape_html(_tipo_documento_label(venta)), estilo_normal)
    caja_dte = Table([
        [titulo_dte],
        [subtitulo_dte],
        [tabla_dte],
    ], colWidths=[200])
    caja_dte.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))

    # ----- MASTER TABLE: encabezado unificado (sin bordes), 60% izquierda / 40% derecha -----
    ancho_total = PAGE_W - 2 * MARGIN
    col_izq = 0.60 * ancho_total
    col_der = 0.40 * ancho_total
    tabla_master = Table([[izquierda_content, caja_dte]], colWidths=[col_izq, col_der])
    tabla_master.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ]))
    elements.append(tabla_master)
    elements.append(Spacer(1, 0.4 * cm))

    # ----- RECEPTOR (Paragraph para nombre, dirección, actividad, correo) -----
    elements.append(Paragraph('<b>RECEPTOR</b>', estilo_bold))
    elements.append(Spacer(1, 4))
    receptor_nombre_p = Paragraph(f"<b>Nombre/Razón Social:</b> {_escape_html(receptor['nombre'])}", estilo_normal)
    receptor_nit_p = Paragraph(f"<b>NIT/DUI:</b> {_escape_html(receptor['nit_dui'])}", estilo_normal)
    receptor_nrc_p = Paragraph(f"<b>NRC:</b> {_escape_html(receptor['nrc'])}", estilo_normal)
    receptor_act_p = Paragraph(f"<b>Actividad Económica:</b> {_escape_html(receptor['actividad_economica'])}", estilo_normal)
    receptor_dir_p = Paragraph(f"<b>Dirección:</b> {_escape_html(receptor['direccion'])}", estilo_normal)
    receptor_correo_p = Paragraph(f"<b>Correo:</b> {_escape_html(receptor['correo'])}", estilo_normal)
    tabla_receptor = Table(
        [[receptor_nombre_p], [receptor_nit_p], [receptor_nrc_p], [receptor_act_p], [receptor_dir_p], [receptor_correo_p]],
        colWidths=[RIGHT - LEFT - 2 * cm],
    )
    tabla_receptor.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(tabla_receptor)
    elements.append(Spacer(1, 0.4 * cm))

    # ----- TABLA DE DETALLE: Descripción como Paragraph para que no se salga -----
    detalles = list(venta.detalles.all()) if hasattr(venta, 'detalles') else []
    col_widths = [1.5 * cm, 1.2 * cm, 8 * cm, 2.5 * cm, 2 * cm, 2 * cm, 2 * cm]
    headers = ['Cantidad', 'Unidad', 'Descripción', 'P. Unitario', 'No Sujetas', 'Exentas', 'Gravadas']
    rows = [headers]
    for d in detalles:
        desc = (d.producto.descripcion if d.producto else d.descripcion_libre) or 'Item'
        desc_paragraph = Paragraph(_escape_html(desc), estilo_normal)
        rows.append([
            f"{_d(d.cantidad):.2f}",
            'UND',
            desc_paragraph,
            f"${_d(d.precio_unitario):.2f}",
            f"${_d(d.venta_no_sujeta):.2f}",
            f"${_d(d.venta_exenta):.2f}",
            f"${_d(d.venta_gravada):.2f}",
        ])
    if not detalles:
        rows.append(['-', '-', Paragraph('Sin ítems', estilo_normal), '-', '-', '-', '-'])

    table_items = Table(rows, colWidths=col_widths)
    table_items.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E5E7EB')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'LEFT'),
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(table_items)
    elements.append(Spacer(1, 0.4 * cm))

    # ----- CÁLCULOS PARA RESUMEN (Pie de página) -----
    venta_gravada = _d(venta.venta_gravada)
    venta_exenta = _d(venta.venta_exenta)
    venta_no_sujeta = _d(venta.venta_no_sujeta)
    debito_fiscal = _d(venta.debito_fiscal)
    iva_ret_1 = _d(venta.iva_retenido_1)
    iva_ret_2 = _d(venta.iva_retenido_2)
    suma_ventas = venta_gravada + venta_exenta + venta_no_sujeta
    descuentos = 0
    subtotal = suma_ventas - descuentos
    total_pagar = round(subtotal + debito_fiscal - iva_ret_1 - iva_ret_2, 2)
    valor_letras = _valor_en_letras(total_pagar)

    # ----- 1. TABLA DE TOTALES (Columna derecha ~35%): solo cálculos numéricos -----
    datos_totales = [
        ['Suma de Ventas:', f"$ {suma_ventas:.2f}"],
        ['Descuento:', f"$ {descuentos:.2f}"],
        ['Sub-Total:', f"$ {subtotal:.2f}"],
        ['IVA 13%:', f"$ {debito_fiscal:.2f}"],
        ['IVA Retenido:', f"$ {iva_ret_1:.2f}"],
    ]
    if iva_ret_2 > 0:
        datos_totales.append(['IVA Percibido:', f"$ {iva_ret_2:.2f}"])
    datos_totales.append(['TOTAL A PAGAR:', f"$ {total_pagar:.2f}"])
    tabla_calculos = Table(datos_totales, colWidths=[3 * cm, 2.5 * cm])
    tabla_calculos.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LINEABOVE', (0, -1), (-1, -1), 1.5, colors.black),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E8E8E8')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 9),
    ]))

    # ----- 2. BLOQUE IZQUIERDO (~65%): Valor en letras, Observaciones, QR, Resolución -----
    valor_letras_p = Paragraph(
        f"<b>SON: {_escape_html(valor_letras)}</b>",
        ParagraphStyle(name='ValorLetras', parent=estilo_normal, fontSize=9, leading=11),
    )
    filas_izq = [[valor_letras_p]]
    observaciones = (getattr(venta, 'observaciones_mh', None) or '').strip()
    if observaciones:
        obs_p = Paragraph(f"<b>Observaciones:</b> {_escape_html(observaciones[:200])}", estilo_normal)
        filas_izq.append([Spacer(1, 8)])
        filas_izq.append([obs_p])
    filas_izq.append([Spacer(1, 10)])
    qr_buf = _generar_qr_imagen_reportlab(url_consulta, size_pt=70)
    if qr_buf:
        try:
            img_qr = Image(qr_buf, width=70, height=70)
            filas_izq.append([Paragraph('<b>Consulta pública MH</b>', ParagraphStyle(name='QRCap', parent=estilo_normal, fontSize=7))])
            filas_izq.append([img_qr])
        except Exception:
            filas_izq.append([Paragraph('<i>QR no disponible</i>', estilo_normal)])
    else:
        filas_izq.append([Paragraph('<i>QR no disponible (instale qrcode[pil])</i>', estilo_normal)])
    numero_resolucion = (getattr(venta, 'numero_resolucion', None) or '').strip()
    serie_documento = (getattr(venta, 'serie_documento', None) or '').strip()
    if numero_resolucion or serie_documento:
        resolucion_texto = []
        if numero_resolucion:
            resolucion_texto.append(f"Resolución No. {_escape_html(numero_resolucion)}")
        if serie_documento:
            resolucion_texto.append(f"Serie {_escape_html(serie_documento)}")
        resolucion_p = Paragraph(
            ' '.join(resolucion_texto),
            ParagraphStyle(name='Resol', parent=estilo_normal, fontSize=7),
        )
        filas_izq.append([Spacer(1, 8)])
        filas_izq.append([resolucion_p])
    ancho_izq_footer = 0.65 * (PAGE_W - 2 * MARGIN)
    contenido_izquierdo = Table(filas_izq, colWidths=[ancho_izq_footer])
    contenido_izquierdo.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))

    # ----- 3. MASTER TABLE DE PIE DE PÁGINA (2 columnas: 65% izq / 35% der) -----
    ancho_total_footer = PAGE_W - 2 * MARGIN
    col_izq_footer = 0.65 * ancho_total_footer
    col_der_footer = 0.35 * ancho_total_footer
    tabla_footer = Table(
        [[contenido_izquierdo, tabla_calculos]],
        colWidths=[col_izq_footer, col_der_footer],
    )
    tabla_footer.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ]))
    elements.append(tabla_footer)

    doc.build(elements)
    buffer.seek(0)
    return buffer
