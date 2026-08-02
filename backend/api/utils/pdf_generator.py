"""
Generador de PDF comercial - Versión legible DTE (MH El Salvador).
Diseño con cabecera de color, 3 temas por empresa (ocean/emerald/amber),
datos obligatorios MH y pie «factura por AgilDTE.com».
"""
import io
import xml.sax.saxutils as saxutils
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlencode

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    KeepTogether,
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

try:
    import qrcode
except ImportError:
    qrcode = None

from api.utils.mh_ubicacion_labels import (
    nombre_departamento as _nombre_departamento_cat,
    nombre_distrito as _nombre_distrito_cat,
    nombre_municipio as _nombre_municipio_cat,
)


MARGIN = 1.2 * cm
PAGE_W, PAGE_H = letter
CONTENT_W = PAGE_W - 2 * MARGIN

TIPOS_ESTABLECIMIENTO = {
    '01': 'Sucursal / Agencia',
    '02': 'Casa Matriz',
    '04': 'Bodega',
    '07': 'Patio',
}

CONDICION_OPERACION = {
    1: 'Contado',
    2: 'Crédito',
    3: 'Otro',
}

# Paletas comerciales (primario oscuro, acento, zebra, texto sobre color)
PDF_TEMAS = {
    'ocean': {
        'primary': colors.HexColor('#0B3A5C'),
        'accent': colors.HexColor('#0D9488'),
        'soft': colors.HexColor('#E6F7F5'),
        'zebra': colors.HexColor('#F0FDFA'),
        'muted': colors.HexColor('#64748B'),
        'border': colors.HexColor('#CBD5E1'),
        'white': colors.white,
        'text': colors.HexColor('#0F172A'),
    },
    'emerald': {
        'primary': colors.HexColor('#064E3B'),
        'accent': colors.HexColor('#059669'),
        'soft': colors.HexColor('#ECFDF5'),
        'zebra': colors.HexColor('#F0FDF4'),
        'muted': colors.HexColor('#64748B'),
        'border': colors.HexColor('#CBD5E1'),
        'white': colors.white,
        'text': colors.HexColor('#0F172A'),
    },
    'amber': {
        'primary': colors.HexColor('#78350F'),
        'accent': colors.HexColor('#D97706'),
        'soft': colors.HexColor('#FFFBEB'),
        'zebra': colors.HexColor('#FEF3C7'),
        'muted': colors.HexColor('#64748B'),
        'border': colors.HexColor('#CBD5E1'),
        'white': colors.white,
        'text': colors.HexColor('#0F172A'),
    },
}


def _palette(empresa):
    key = (getattr(empresa, 'pdf_tema_color', None) or 'ocean').strip().lower()
    return PDF_TEMAS.get(key, PDF_TEMAS['ocean'])


def _escape_html(text):
    if not text:
        return ""
    return saxutils.escape(str(text).strip())


def _solo_digitos(valor):
    if valor is None:
        return ''
    return ''.join(c for c in str(valor) if c.isdigit())


def _formatear_nit_display(valor):
    digitos = _solo_digitos(valor)
    if len(digitos) == 14:
        return f"{digitos[:4]}-{digitos[4:10]}-{digitos[10:13]}-{digitos[13]}"
    if len(digitos) == 9:
        return f"{digitos[:8]}-{digitos[8]}"
    return (str(valor).strip() if valor else '') or 'N/A'


def _formatear_nrc_display(valor):
    digitos = _solo_digitos(valor)
    if len(digitos) >= 2:
        return f"{digitos[:-1]}-{digitos[-1]}"
    return digitos or 'N/A'


def _nombre_departamento(codigo):
    nombre = _nombre_departamento_cat(codigo)
    return (
        nombre.upper()
        .replace('Á', 'A').replace('É', 'E').replace('Í', 'I')
        .replace('Ó', 'O').replace('Ú', 'U')
    )


def _armar_direccion(complemento, departamento_codigo, municipio_codigo=None, distrito_codigo=None):
    partes = []
    comp = (complemento or '').strip().rstrip(',')
    if comp:
        partes.append(comp)
    dist_nom = _nombre_distrito_cat(departamento_codigo, municipio_codigo, distrito_codigo)
    if dist_nom:
        partes.append(f'Distrito {dist_nom}')
    muni_nom = _nombre_municipio_cat(departamento_codigo, municipio_codigo)
    if muni_nom:
        partes.append(muni_nom)
    depto = _nombre_departamento(departamento_codigo)
    if depto:
        partes.append(depto)
    return ', '.join(partes)


def _linea_si(etiqueta, valor):
    """Devuelve línea HTML solo si hay valor útil (excluye vacío / N/A)."""
    txt = str(valor or '').strip()
    if not txt or txt.upper() in ('N/A', 'NA', '-', 'NONE', 'NULL'):
        return None
    return f"<b>{etiqueta}:</b> {_escape_html(txt)}"


def _agregar_lineas(destino, pares):
    for etiqueta, valor in pares:
        ln = _linea_si(etiqueta, valor)
        if ln:
            destino.append(ln)


def _condicion_operacion_label(venta):
    try:
        codigo = int(getattr(venta, 'condicion_operacion', 1) or 1)
    except (TypeError, ValueError):
        codigo = 1
    return CONDICION_OPERACION.get(codigo, 'Contado')


def _modelo_transmision(venta):
    estado = (getattr(venta, 'estado_dte', None) or '').strip().upper()
    if estado in ('CONTINGENCIA', 'PENDIENTEENVIO', 'PENDIENTE_ENVIO'):
        return 'Diferido', 'Contingencia'
    return 'Previo', 'Normal'


def _formatear_fecha_hora(venta):
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
    try:
        total = float(Decimal(str(total_pagar)))
    except (TypeError, ValueError):
        return "CERO DOLARES CON 00/100 USD"
    entero = int(total)
    centavos = round((total - entero) * 100)
    if centavos >= 100:
        centavos = 0
        entero += 1
    centavos_str = f"{centavos:02d}"
    if num2words:
        try:
            palabras = num2words(entero, lang='es')
            palabras = (
                palabras.upper()
                .replace('Á', 'A').replace('É', 'E').replace('Í', 'I')
                .replace('Ó', 'O').replace('Ú', 'U')
            )
        except Exception:
            palabras = str(entero)
    else:
        palabras = str(entero)
    return f"{palabras} DOLARES CON {centavos_str}/100 USD"


def _obtener_ruta_logo(empresa):
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
    if not qrcode:
        return None
    try:
        qr = qrcode.QRCode(version=1, box_size=3, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
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
    try:
        return float(Decimal(str(val or default)))
    except (TypeError, ValueError):
        return float(default)


def _obtener_datos_emisor(venta):
    empresa = venta.empresa
    if not empresa:
        return {
            'nombre': 'EMPRESA S.A. DE C.V.',
            'nombre_comercial': '',
            'nrc': '',
            'nit': '',
            'actividad_economica': '',
            'direccion': '',
            'municipio': '',
            'distrito': '',
            'departamento': '',
            'telefono': '',
            'correo': '',
            'tipo_establecimiento': '',
            'cod_establecimiento': '',
        }
    nombre = (empresa.nombre or 'EMPRESA S.A. DE C.V.').strip()
    nombre_comercial = (getattr(empresa, 'nombre_comercial', None) or '').strip()
    cod_act = (getattr(empresa, 'cod_actividad', None) or '').strip()
    desc_act = (getattr(empresa, 'desc_actividad', None) or '').strip()
    if desc_act and cod_act:
        actividad = f"{cod_act} - {desc_act}"
    elif desc_act:
        actividad = desc_act
    elif cod_act:
        actividad = cod_act
    else:
        actividad = ''

    depto = (getattr(empresa, 'departamento', None) or '').strip()
    muni = (getattr(empresa, 'municipio', None) or '').strip()
    dist = (getattr(empresa, 'distrito', None) or '').strip()
    complemento = (getattr(empresa, 'direccion', None) or '').strip()
    cod_est = (getattr(empresa, 'cod_establecimiento', None) or '').strip()
    tipo_est = TIPOS_ESTABLECIMIENTO.get('01', 'Sucursal / Agencia')
    if cod_est and cod_est in TIPOS_ESTABLECIMIENTO:
        tipo_est = TIPOS_ESTABLECIMIENTO[cod_est]
    elif cod_est:
        tipo_est = f"{TIPOS_ESTABLECIMIENTO.get('01', 'Sucursal / Agencia')} ({cod_est})"

    return {
        'nombre': nombre,
        'nombre_comercial': nombre_comercial if nombre_comercial != nombre else '',
        'nrc': _formatear_nrc_display(empresa.nrc) if empresa.nrc else '',
        'nit': _formatear_nit_display(empresa.nit or '') if empresa.nit else '',
        'actividad_economica': actividad,
        'direccion': _armar_direccion(complemento, depto, muni, dist),
        'complemento': complemento,
        'municipio': _nombre_municipio_cat(depto, muni),
        'distrito': _nombre_distrito_cat(depto, muni, dist),
        'departamento': _nombre_departamento_cat(depto),
        'telefono': (getattr(empresa, 'telefono', None) or '').strip(),
        'correo': (getattr(empresa, 'correo', None) or '').strip(),
        'tipo_establecimiento': tipo_est,
        'cod_establecimiento': cod_est,
    }


def _obtener_datos_receptor(venta):
    tipo_venta = (getattr(venta, 'tipo_venta', None) or '').strip().upper()

    nombre = (venta.nombre_receptor or '').strip()
    if not nombre and venta.cliente:
        nombre = (venta.cliente.nombre or '').strip()
    if not nombre:
        nombre = 'Consumidor Final'

    nombre_comercial = (getattr(venta, 'nombre_comercial_receptor', None) or '').strip()
    if not nombre_comercial and venta.cliente:
        nombre_comercial = (getattr(venta.cliente, 'nombre_comercial', None) or '').strip()
    if nombre_comercial and nombre_comercial.lower() == nombre.lower():
        nombre_comercial = ''

    nrc = (venta.nrc_receptor or '').strip()
    if not nrc and venta.cliente:
        nrc = (venta.cliente.nrc or '').strip()

    nit_dui = (venta.documento_receptor or '').strip()
    if not nit_dui and venta.cliente:
        nit_dui = (venta.cliente.documento_identidad or venta.cliente.nit or venta.cliente.dui or '').strip()

    direccion_comp = (venta.direccion_receptor or '').strip()
    if not direccion_comp and venta.cliente:
        direccion_comp = (getattr(venta.cliente, 'direccion', None) or '').strip()

    depto = (getattr(venta, 'departamento_receptor', None) or '').strip()
    muni = (getattr(venta, 'municipio_receptor', None) or '').strip()
    dist = (getattr(venta, 'distrito_receptor', None) or '').strip()
    if venta.cliente:
        if not depto:
            depto = (getattr(venta.cliente, 'departamento', None) or '').strip()
        if not muni:
            muni = (getattr(venta.cliente, 'municipio', None) or '').strip()
        if not dist:
            dist = (getattr(venta.cliente, 'distrito', None) or '').strip()

    correo = (venta.correo_receptor or '').strip()
    if not correo and venta.cliente:
        correo = (getattr(venta.cliente, 'email_contacto', None) or '').strip()

    telefono = (getattr(venta, 'telefono_receptor', None) or '').strip() if hasattr(venta, 'telefono_receptor') else ''
    if not telefono and venta.cliente:
        telefono = (getattr(venta.cliente, 'telefono', None) or '').strip()

    actividad = ''
    cod = (getattr(venta, 'cod_actividad_receptor', None) or '').strip()
    desc = (getattr(venta, 'desc_actividad_receptor', None) or '').strip()
    if not cod and not desc and venta.cliente:
        cod = (getattr(venta.cliente, 'cod_actividad', None) or '').strip()
        desc = (getattr(venta.cliente, 'desc_actividad', None) or '').strip()
    if cod and desc:
        actividad = f"{cod} - {desc}"
    elif desc:
        actividad = desc
    elif cod:
        actividad = cod

    tipo_doc = (getattr(venta, 'tipo_doc_receptor', None) or '').strip().upper()
    if not tipo_doc and venta.cliente:
        tipo_doc = (getattr(venta.cliente, 'tipo_documento', None) or '').strip().upper()
    if tipo_doc in ('DUI', '13'):
        etiqueta_doc = 'DUI'
        doc_display = nit_dui or ''
    elif tipo_doc in ('NIT', '36'):
        etiqueta_doc = 'NIT'
        doc_display = _formatear_nit_display(nit_dui) if nit_dui else ''
    else:
        etiqueta_doc = 'NIT' if (nit_dui and len(''.join(c for c in nit_dui if c.isdigit())) >= 14) else 'Documento'
        doc_display = _formatear_nit_display(nit_dui) if nit_dui and etiqueta_doc == 'NIT' else (nit_dui or '')

    return {
        'nombre': nombre,
        'nombre_comercial': nombre_comercial,
        'etiqueta_doc': etiqueta_doc,
        'nit_dui': doc_display,
        'nrc': _formatear_nrc_display(nrc) if nrc else '',
        'actividad_economica': actividad,
        'direccion': _armar_direccion(direccion_comp, depto, muni, dist),
        'complemento': direccion_comp,
        'municipio': _nombre_municipio_cat(depto, muni),
        'distrito': _nombre_distrito_cat(depto, muni, dist),
        'departamento': _nombre_departamento_cat(depto),
        'correo': correo or '',
        'telefono': telefono or '',
        'tipo_venta': tipo_venta,
    }


def _tipo_documento_label(venta):
    tipo = (venta.tipo_venta or 'CF').upper()
    if tipo == 'CCF':
        return 'COMPROBANTE DE CRÉDITO FISCAL'
    if tipo == 'NC':
        return 'NOTA DE CRÉDITO'
    if tipo == 'ND':
        return 'NOTA DE DÉBITO'
    if tipo == 'FSE':
        return 'FACTURA SUJETO EXCLUIDO'
    return 'FACTURA'


def _tipo_documento_corto(venta):
    tipo = (venta.tipo_venta or 'CF').upper()
    if tipo == 'CCF':
        return 'CRÉDITO FISCAL'
    if tipo == 'NC':
        return 'NOTA DE CRÉDITO'
    if tipo == 'ND':
        return 'NOTA DE DÉBITO'
    if tipo == 'FSE':
        return 'SUJETO EXCLUIDO'
    return 'FACTURA'


def generar_pdf_venta(venta):
    """
    Genera PDF comercial (versión legible DTE) con tema de color de la empresa.
    Returns: BytesIO
    """
    buffer = io.BytesIO()
    empresa = venta.empresa
    pal = _palette(empresa)
    styles = getSampleStyleSheet()

    estilo_normal = ParagraphStyle(
        name='NormalWrap', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8, leading=10,
        textColor=pal['text'], wordWrap='CJK',
    )
    estilo_bold = ParagraphStyle(
        name='BoldWrap', parent=estilo_normal, fontName='Helvetica-Bold',
    )
    estilo_sello = ParagraphStyle(
        name='SelloSmall', parent=estilo_normal, fontSize=6, leading=8, wordWrap='CJK',
    )
    estilo_header_white = ParagraphStyle(
        name='HeaderWhite', parent=estilo_normal,
        fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=pal['white'],
    )
    estilo_title_white = ParagraphStyle(
        name='TitleWhite', parent=estilo_normal,
        fontName='Helvetica-Bold', fontSize=14, leading=17, textColor=pal['white'],
        alignment=2,  # RIGHT
    )
    estilo_sub_white = ParagraphStyle(
        name='SubWhite', parent=estilo_normal,
        fontSize=8, leading=10, textColor=pal['white'], alignment=2,
    )
    estilo_section = ParagraphStyle(
        name='Section', parent=estilo_bold,
        fontSize=9, leading=11, textColor=pal['primary'],
    )
    estilo_footer = ParagraphStyle(
        name='FooterTiny', parent=estilo_normal,
        fontSize=7, leading=9, textColor=pal['muted'], alignment=1,
    )
    estilo_celda = ParagraphStyle(
        name='CeldaTiny', parent=estilo_normal, fontSize=7, leading=9,
    )
    estilo_th = ParagraphStyle(
        name='TH', parent=estilo_normal,
        fontName='Helvetica-Bold', fontSize=7, leading=8, textColor=pal['white'],
    )

    emisor = _obtener_datos_emisor(venta)
    receptor = _obtener_datos_receptor(venta)
    fecha_hora = _formatear_fecha_hora(venta)
    codigo_gen = (venta.codigo_generacion or '').strip() or 'N/A'
    numero_control = (venta.numero_control or venta.numero_documento or '').strip() or 'N/A'
    sello = (venta.sello_recepcion or '').strip() or 'N/A'
    codigo_gen_raw = (venta.codigo_generacion or '').strip()
    fecha_iso = venta.fecha_emision.strftime('%Y-%m-%d') if venta.fecha_emision else ''
    modelo_fact, tipo_trans = _modelo_transmision(venta)
    condicion_op = _condicion_operacion_label(venta)
    ambiente_venta = (
        getattr(venta, 'ambiente_emision', None)
        or getattr(empresa, 'ambiente', None)
        or '01'
    )
    if codigo_gen_raw:
        params = {'ambiente': ambiente_venta, 'codGen': codigo_gen_raw}
        if fecha_iso:
            params['fechaEmi'] = fecha_iso
        url_consulta = f"https://admin.factura.gob.sv/consultaPublica?{urlencode(params)}"
    else:
        url_consulta = ''

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )
    elements = []

    # ----- CABECERA DE COLOR -----
    logo_path = _obtener_ruta_logo(empresa) if empresa else None
    img_logo = None
    if logo_path:
        try:
            img_logo = Image(logo_path, width=72, height=40)
        except Exception:
            img_logo = None

    brand_lines = [
        Paragraph(f"<b>{_escape_html(emisor['nombre'])}</b>", estilo_header_white),
        Paragraph(
            f"NRC: {_escape_html(emisor['nrc'])}  ·  NIT: {_escape_html(emisor['nit'])}",
            ParagraphStyle(name='BrandMeta', parent=estilo_header_white, fontName='Helvetica', fontSize=7),
        ),
    ]
    # Con logo: columna logo + 2 cm de separación + texto (evita nombre/NRC sobre el logo).
    brand_text_w = 7.2 * cm if img_logo else 11.7 * cm
    brand_cell = Table([[p] for p in brand_lines], colWidths=[brand_text_w])
    brand_cell.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BACKGROUND', (0, 0), (-1, -1), pal['primary']),
    ]))

    if img_logo:
        left_brand = [[img_logo, '', brand_cell]]
        left_w = [2.5 * cm, 2.0 * cm, brand_text_w]
    else:
        left_brand = [[brand_cell]]
        left_w = [brand_text_w]
    left_header = Table(left_brand, colWidths=left_w)
    left_header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, -1), pal['primary']),
        ('LEFTPADDING', (0, 0), (0, 0), 6),
        ('RIGHTPADDING', (0, 0), (0, 0), 0),
        ('LEFTPADDING', (1, 0), (-1, -1), 0),
        ('RIGHTPADDING', (1, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))

    right_header = Table([
        [Paragraph('DOCUMENTO TRIBUTARIO ELECTRÓNICO', estilo_sub_white)],
        [Paragraph(_escape_html(_tipo_documento_corto(venta)), estilo_title_white)],
    ], colWidths=[6.5 * cm])
    right_header.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), pal['accent']),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))

    header = Table([[left_header, right_header]], colWidths=[CONTENT_W * 0.62, CONTENT_W * 0.38])
    header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(header)
    # Franja acento
    accent_bar = Table([['']], colWidths=[CONTENT_W], rowHeights=[4])
    accent_bar.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), pal['accent']),
    ]))
    elements.append(accent_bar)
    elements.append(Spacer(1, 0.35 * cm))

    # ----- CAJA DTE + QR -----
    qr_buf = _generar_qr_imagen_reportlab(url_consulta, size_pt=78) if url_consulta else None
    img_qr = None
    if qr_buf:
        try:
            img_qr = Image(qr_buf, width=72, height=72)
        except Exception:
            img_qr = None

    datos_criticos = [
        ('Código de Generación', codigo_gen),
        ('Número de Control', numero_control),
        ('Sello de Recepción', sello),
        ('Fecha y Hora', fecha_hora),
        ('Modelo', modelo_fact),
        ('Transmisión', tipo_trans),
    ]
    filas_dte = []
    for label, value in datos_criticos:
        estilo_val = estilo_sello if label.startswith('Sello') else estilo_normal
        filas_dte.append([
            Paragraph(f"<b>{_escape_html(label)}</b>", estilo_normal),
            Paragraph(_escape_html(value), estilo_val),
        ])
    tabla_dte = Table(filas_dte, colWidths=[3.4 * cm, 8.2 * cm])
    tabla_dte.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (0, -1), pal['soft']),
        ('TEXTCOLOR', (0, 0), (-1, -1), pal['text']),
        ('BOX', (0, 0), (-1, -1), 0.8, pal['border']),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, pal['border']),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))

    qr_block = []
    if img_qr:
        qr_block = [
            [Paragraph('<b>Consulta MH</b>', ParagraphStyle(
                name='QRLab', parent=estilo_normal, fontSize=7, alignment=1, textColor=pal['primary'],
            ))],
            [img_qr],
        ]
    else:
        qr_block = [[Paragraph('<i>QR N/D</i>', estilo_normal)]]
    tabla_qr = Table(qr_block, colWidths=[3.2 * cm])
    tabla_qr.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 0.8, pal['border']),
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))

    meta_row = Table([[tabla_dte, tabla_qr]], colWidths=[CONTENT_W - 3.6 * cm, 3.6 * cm])
    meta_row.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(meta_row)
    elements.append(Spacer(1, 0.35 * cm))

    # ----- EMISOR / RECEPTOR -----
    def _bloque_persona(titulo, lineas):
        head = Paragraph(titulo, estilo_section)
        body = [[Paragraph(ln, estilo_normal)] for ln in lineas]
        body_t = Table(body, colWidths=[CONTENT_W * 0.47])
        body_t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('BACKGROUND', (0, 0), (-1, -1), pal['soft']),
        ]))
        wrap = Table([[head], [body_t]], colWidths=[CONTENT_W * 0.48])
        wrap.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), colors.white),
            ('BOTTOMPADDING', (0, 0), (0, 0), 3),
            ('BOX', (0, 1), (0, 1), 0.8, pal['border']),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        return wrap

    lineas_emisor = []
    _agregar_lineas(lineas_emisor, [
        ('Nombre', emisor.get('nombre')),
        ('NRC', emisor.get('nrc')),
        ('NIT', emisor.get('nit')),
        ('Actividad', emisor.get('actividad_economica')),
        ('Dirección', emisor.get('complemento') or emisor.get('direccion')),
        ('Municipio', emisor.get('municipio')),
        ('Distrito', emisor.get('distrito')),
        ('Departamento', emisor.get('departamento')),
        ('Tel', emisor.get('telefono')),
        ('Correo', emisor.get('correo')),
        ('Nombre comercial', emisor.get('nombre_comercial')),
        ('Establecimiento', emisor.get('tipo_establecimiento')),
    ])

    lineas_receptor = []
    _agregar_lineas(lineas_receptor, [
        ('Nombre', receptor.get('nombre')),
        ('Nombre comercial', receptor.get('nombre_comercial')),
        (receptor.get('etiqueta_doc') or 'Documento', receptor.get('nit_dui')),
        ('NRC', receptor.get('nrc')),
        ('Actividad', receptor.get('actividad_economica')),
        ('Dirección', receptor.get('complemento') or receptor.get('direccion')),
        ('Municipio', receptor.get('municipio')),
        ('Distrito', receptor.get('distrito')),
        ('Departamento', receptor.get('departamento')),
        ('Tel', receptor.get('telefono')),
        ('Correo', receptor.get('correo')),
    ])
    if not lineas_receptor:
        lineas_receptor.append('<b>Nombre:</b> Consumidor Final')

    bloques = Table(
        [[_bloque_persona('EMISOR', lineas_emisor), _bloque_persona('RECEPTOR', lineas_receptor)]],
        colWidths=[CONTENT_W * 0.5, CONTENT_W * 0.5],
    )
    bloques.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (0, 0), 4),
        ('LEFTPADDING', (1, 0), (1, 0), 4),
    ]))
    elements.append(bloques)
    elements.append(Spacer(1, 0.3 * cm))

    # ----- DOCUMENTOS RELACIONADOS -----
    tipo_venta_doc = (getattr(venta, 'tipo_venta', None) or '').strip().upper()
    doc_rel_num = (
        (getattr(venta, 'codigo_generacion_referenciado', None) or '').strip()
        or (getattr(venta, 'documento_relacionado_numero_control', None) or '').strip()
    )
    if tipo_venta_doc in ('NC', 'ND') and doc_rel_num:
        elements.append(Paragraph('DOCUMENTOS RELACIONADOS', estilo_section))
        elements.append(Spacer(1, 3))
        tipo_rel = (getattr(venta, 'documento_relacionado_tipo', None) or '').strip() or '-'
        fecha_rel = getattr(venta, 'documento_relacionado_fecha_emision', None)
        fecha_rel_txt = fecha_rel.strftime('%d/%m/%Y') if fecha_rel else '-'
        tabla_rel = Table(
            [
                [
                    Paragraph('<b>Tipo</b>', estilo_th),
                    Paragraph('<b>N° de Documento</b>', estilo_th),
                    Paragraph('<b>Fecha</b>', estilo_th),
                ],
                [
                    Paragraph(_escape_html(tipo_rel), estilo_celda),
                    Paragraph(_escape_html(doc_rel_num), estilo_celda),
                    Paragraph(_escape_html(fecha_rel_txt), estilo_celda),
                ],
            ],
            colWidths=[2.5 * cm, CONTENT_W - 5.5 * cm, 3 * cm],
        )
        tabla_rel.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), pal['primary']),
            ('GRID', (0, 0), (-1, -1), 0.4, pal['border']),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(tabla_rel)
        elements.append(Spacer(1, 0.25 * cm))

    # ----- DETALLE -----
    detalles = list(venta.detalles.all()) if hasattr(venta, 'detalles') else []
    es_cf = getattr(venta, 'tipo_venta', None) == 'CF'
    col_widths = [0.7 * cm, 1.2 * cm, 1.2 * cm, 5.4 * cm, 2.0 * cm, 1.5 * cm, 1.7 * cm, 1.7 * cm, 2.0 * cm]
    headers = [
        Paragraph('N°', estilo_th),
        Paragraph('Cant.', estilo_th),
        Paragraph('Unidad', estilo_th),
        Paragraph('Descripción', estilo_th),
        Paragraph('P. Unit.', estilo_th),
        Paragraph('Desc.', estilo_th),
        Paragraph('No Suj.', estilo_th),
        Paragraph('Exentas', estilo_th),
        Paragraph('Gravadas', estilo_th),
    ]
    rows = [headers]
    for idx, d in enumerate(detalles, start=1):
        desc = (d.producto.descripcion if d.producto else d.descripcion_libre) or 'Item'
        if es_cf and (_d(d.venta_gravada) + _d(d.iva_item)) > 0:
            total_linea = _d(d.venta_gravada) + _d(d.iva_item)
            p_unit = total_linea / _d(d.cantidad) if _d(d.cantidad) else total_linea
            gravada_col = total_linea
        else:
            p_unit = _d(d.precio_unitario)
            gravada_col = _d(d.venta_gravada)
        num_item = getattr(d, 'numero_item', None) or idx
        rows.append([
            str(num_item),
            f"{_d(d.cantidad):.2f}",
            'Unidad',
            Paragraph(_escape_html(desc), estilo_celda),
            f"${p_unit:,.2f}",
            f"${_d(d.monto_descuento):,.2f}",
            f"${_d(d.venta_no_sujeta):,.2f}",
            f"${_d(d.venta_exenta):,.2f}",
            f"${gravada_col:,.2f}",
        ])
    if not detalles:
        rows.append(['-', '-', '-', Paragraph('Sin ítems', estilo_celda), '-', '-', '-', '-', '-'])

    table_items = Table(rows, colWidths=col_widths)
    item_style = [
        ('BACKGROUND', (0, 0), (-1, 0), pal['primary']),
        ('TEXTCOLOR', (0, 0), (-1, 0), pal['white']),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
        ('ALIGN', (3, 0), (3, -1), 'LEFT'),
        ('ALIGN', (4, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.4, pal['border']),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
    ]
    for i in range(1, len(rows)):
        if i % 2 == 0:
            item_style.append(('BACKGROUND', (0, i), (-1, i), pal['zebra']))
    table_items.setStyle(TableStyle(item_style))
    elements.append(table_items)
    elements.append(Spacer(1, 0.3 * cm))

    # ----- TOTALES -----
    venta_gravada = _d(venta.venta_gravada)
    venta_exenta = _d(venta.venta_exenta)
    venta_no_sujeta = _d(venta.venta_no_sujeta)
    debito_fiscal = _d(venta.debito_fiscal)
    iva_ret_1 = _d(venta.iva_retenido_1)
    iva_ret_2 = _d(venta.iva_retenido_2)
    tipo_venta = (getattr(venta, 'tipo_venta', None) or '').strip().upper()
    es_cf = tipo_venta == 'CF'
    if es_cf:
        suma_ventas = round(venta_gravada + debito_fiscal + venta_exenta + venta_no_sujeta, 2)
        gravadas_display = suma_ventas - venta_exenta - venta_no_sujeta
    else:
        suma_ventas = venta_gravada + venta_exenta + venta_no_sujeta
        gravadas_display = venta_gravada
    descuentos = 0
    subtotal = suma_ventas - descuentos
    monto_total_operacion = subtotal + (0 if es_cf else debito_fiscal)
    total_pagar = round(monto_total_operacion - iva_ret_1 - iva_ret_2, 2)
    valor_letras = _valor_en_letras(total_pagar)

    datos_totales = [
        ['Ventas No Sujetas:', f"$ {venta_no_sujeta:,.2f}"],
        ['Ventas Exentas:', f"$ {venta_exenta:,.2f}"],
        ['Ventas Gravadas:', f"$ {gravadas_display:,.2f}"],
        ['Sumatoria de ventas:', f"$ {suma_ventas:,.2f}"],
        ['Descuento:', f"$ {descuentos:,.2f}"],
        ['Sub-Total:', f"$ {subtotal:,.2f}"],
    ]
    if not es_cf:
        datos_totales.append(['IVA 13%:', f"$ {debito_fiscal:,.2f}"])
    datos_totales.append(['IVA Retenido:', f"$ {iva_ret_1:,.2f}"])
    if iva_ret_2 > 0:
        datos_totales.append(['IVA Percibido:', f"$ {iva_ret_2:,.2f}"])
    datos_totales.append(['Monto Total Operación:', f"$ {monto_total_operacion:,.2f}"])
    datos_totales.append(['TOTAL A PAGAR:', f"$ {total_pagar:,.2f}"])

    tabla_calculos = Table(datos_totales, colWidths=[3.8 * cm, 2.5 * cm])
    n_tot = len(datos_totales)
    calc_style = [
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TEXTCOLOR', (0, 0), (-1, -2), pal['text']),
        ('BACKGROUND', (0, n_tot - 1), (-1, n_tot - 1), pal['accent']),
        ('TEXTCOLOR', (0, n_tot - 1), (-1, n_tot - 1), pal['white']),
        ('FONTNAME', (0, n_tot - 1), (-1, n_tot - 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, n_tot - 1), (-1, n_tot - 1), 9),
        ('TOPPADDING', (0, n_tot - 1), (-1, n_tot - 1), 6),
        ('BOTTOMPADDING', (0, n_tot - 1), (-1, n_tot - 1), 6),
        ('BOX', (0, 0), (-1, -2), 0.5, pal['border']),
    ]
    tabla_calculos.setStyle(TableStyle(calc_style))

    observaciones = (getattr(venta, 'observaciones', None) or '').strip() or '-'
    info_izq = [
        [Paragraph(f"<b>Valor en Letras:</b> {_escape_html(valor_letras)}", estilo_normal)],
        [Spacer(1, 4)],
        [Paragraph(f"<b>Condición de la Operación:</b> {_escape_html(condicion_op)}", estilo_normal)],
        [Spacer(1, 4)],
        [Paragraph(f"<b>Observaciones:</b> {_escape_html(observaciones[:200])}", estilo_normal)],
    ]
    numero_resolucion = (getattr(venta, 'numero_resolucion', None) or '').strip()
    serie_documento = (getattr(venta, 'serie_documento', None) or '').strip()
    if numero_resolucion or serie_documento:
        partes = []
        if numero_resolucion:
            partes.append(f"Resolución No. {_escape_html(numero_resolucion)}")
        if serie_documento:
            partes.append(f"Serie {_escape_html(serie_documento)}")
        info_izq.append([Spacer(1, 4)])
        info_izq.append([Paragraph(' '.join(partes), ParagraphStyle(
            name='Resol', parent=estilo_normal, fontSize=7, textColor=pal['muted'],
        ))])

    contenido_izquierdo = Table(info_izq, colWidths=[CONTENT_W * 0.55])
    contenido_izquierdo.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))

    footer_row = Table(
        [[contenido_izquierdo, tabla_calculos]],
        colWidths=[CONTENT_W * 0.58, CONTENT_W * 0.42],
    )
    footer_row.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ]))
    elements.append(footer_row)
    elements.append(Spacer(1, 0.45 * cm))

    # ----- PIE AgilDTE -----
    contact_bits = []
    if emisor.get('telefono'):
        contact_bits.append(f"Tel: {_escape_html(emisor['telefono'])}")
    if emisor.get('correo'):
        contact_bits.append(_escape_html(emisor['correo']))
    contact_line = '  ·  '.join(contact_bits) if contact_bits else ''

    pie_bar = Table(
        [
            [Paragraph('Gracias por su confianza', ParagraphStyle(
                name='Thanks', parent=estilo_normal, fontSize=8, alignment=1,
                textColor=pal['primary'], fontName='Helvetica-Bold',
            ))],
            [Paragraph(contact_line, estilo_footer)] if contact_line else [Spacer(1, 1)],
            [Paragraph('factura por AgilDTE.com', estilo_footer)],
        ],
        colWidths=[CONTENT_W],
    )
    pie_bar.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), pal['soft']),
        ('BOX', (0, 0), (-1, -1), 0.5, pal['border']),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(KeepTogether([pie_bar]))

    doc.build(elements)
    buffer.seek(0)
    return buffer
