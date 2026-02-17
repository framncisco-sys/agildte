"""
Utilidades para reportes de Libros de IVA (Consumidor Final y Contribuyentes).
Estructura alineada con CSV de referencia MH.
"""
import csv
import io
from decimal import Decimal

from django.http import HttpResponse

# Ventas consideradas "PROCESADAS" (aceptadas o enviadas a MH)
ESTADO_PROCESADO = ['AceptadoMH', 'Enviado']


def _f(n):
    """Float seguro."""
    try:
        return float(Decimal(str(n or 0)))
    except (TypeError, ValueError):
        return 0.0


def get_datos_libro_consumidor(empresa_id, mes, anio):
    """
    Libro de ventas a Consumidor Final (DTE-01).
    Filtro: tipo_venta='CF', estado_dte en AceptadoMH/Enviado, periodo mes/anio.
    """
    from ..models import Venta
    periodo = f"{anio}-{mes:02d}"
    ventas = Venta.objects.filter(
        empresa_id=empresa_id,
        periodo_aplicado=periodo,
        tipo_venta='CF',
        estado_dte__in=ESTADO_PROCESADO,
    ).order_by('fecha_emision', 'id')
    datos = []
    t_exentas = t_gravadas = t_no_sujetas = t_total = 0.0
    for v in ventas:
        clase_doc = 'Electrónico' if v.clase_documento == '4' else 'Físico'
        venta_exenta = venta_gravada = venta_no_sujeta = 0.0
        debito = _f(v.debito_fiscal)
        # Total de la línea: en CF el gravado suele ir con IVA incluido
        total_venta = _f(v.venta_gravada) + _f(v.venta_exenta) + _f(v.venta_no_sujeta) + debito
        if (v.clasificacion_venta or '').strip() == '2':
            venta_exenta = total_venta
        elif (v.clasificacion_venta or '').strip() == '3':
            venta_no_sujeta = total_venta
        else:
            venta_gravada = _f(v.venta_gravada) + debito
        total_venta = venta_exenta + venta_gravada + venta_no_sujeta
        t_exentas += venta_exenta
        t_gravadas += venta_gravada
        t_no_sujetas += venta_no_sujeta
        t_total += total_venta
        # Para CSV formato MH: codigo/sello sin guiones, numero DTE style
        codigo_limpio = (str(v.codigo_generacion or '')).replace('-', '').upper()
        sello_limpio = (str(v.sello_recepcion or '')).replace('-', '').upper()
        numero_dte = (v.numero_control or v.numero_documento or '').strip()
        clase_raw = v.clase_documento or '4'
        datos.append({
            'fecha_emision': v.fecha_emision.strftime('%d/%m/%Y'),
            'clase_documento': clase_doc,
            'tipo_documento': '01',
            'numero_resolucion': v.numero_resolucion or '',
            'serie': v.serie_documento if v.clase_documento != '4' else 'DTE',
            'numero_control': v.numero_control or v.numero_documento or '',
            'ventas_exentas': round(venta_exenta, 2),
            'ventas_internas_gravadas': round(venta_gravada, 2),
            'ventas_no_sujetas': round(venta_no_sujeta, 2),
            'total_ventas': round(total_venta, 2),
            # Campos para CSV formato MH (VentaConsumidor)
            'clase_raw': clase_raw,
            'numero_dte': numero_dte,
            'codigo_generacion': codigo_limpio,
            'sello_recepcion': sello_limpio,
            'clasificacion_venta': (v.clasificacion_venta or '1').strip(),
            'tipo_ingreso': (v.tipo_ingreso or '2').strip(),
        })
    totales = {
        'ventas_exentas': round(t_exentas, 2),
        'ventas_internas_gravadas': round(t_gravadas, 2),
        'ventas_no_sujetas': round(t_no_sujetas, 2),
        'total_ventas': round(t_total, 2),
    }
    return {'datos': datos, 'totales': totales, 'periodo': periodo}


def get_datos_libro_contribuyentes(empresa_id, mes, anio):
    """
    Libro de ventas a Contribuyentes (DTE-03).
    Filtro: tipo_venta='CCF', estado_dte en AceptadoMH/Enviado, periodo mes/anio.
    """
    from ..models import Venta
    periodo = f"{anio}-{mes:02d}"
    ventas = Venta.objects.filter(
        empresa_id=empresa_id,
        periodo_aplicado=periodo,
        tipo_venta='CCF',
        estado_dte__in=ESTADO_PROCESADO,
    ).order_by('fecha_emision', 'id').select_related('cliente')
    datos = []
    t_neto = t_debito = t_total = 0.0
    for v in ventas:
        monto_neto = _f(v.venta_gravada)
        debito_fiscal = _f(v.debito_fiscal)
        total_venta = monto_neto + debito_fiscal
        t_neto += monto_neto
        t_debito += debito_fiscal
        t_total += total_venta
        nombre_cliente = (v.nombre_receptor or (v.cliente.nombre if v.cliente else '') or '').strip()
        nrc_cliente = (v.nrc_receptor or (v.cliente.nrc if v.cliente else '') or '').strip()
        codigo_limpio = (str(v.codigo_generacion or '')).replace('-', '').upper()
        sello_limpio = (str(v.sello_recepcion or '')).replace('-', '').upper()
        numero_dte = (v.numero_control or v.numero_documento or '').strip()
        clase_raw = v.clase_documento or '4'
        datos.append({
            'fecha_emision': v.fecha_emision.strftime('%d/%m/%Y'),
            'numero_control': v.numero_control or v.numero_documento or '',
            'nombre_cliente': nombre_cliente,
            'nrc_cliente': nrc_cliente,
            'monto_neto': round(monto_neto, 2),
            'debito_fiscal': round(debito_fiscal, 2),
            'total_venta': round(total_venta, 2),
            # Para CSV formato MH (VentaContribuyentes)
            'clase_raw': clase_raw,
            'numero_dte': numero_dte,
            'numero_resolucion': v.numero_resolucion or '',
            'codigo_generacion': codigo_limpio,
            'sello_recepcion': sello_limpio,
            'clasificacion_venta': (v.clasificacion_venta or '1').strip(),
            'tipo_ingreso': (v.tipo_ingreso or '2').strip(),
        })
    totales = {
        'monto_neto': round(t_neto, 2),
        'debito_fiscal': round(t_debito, 2),
        'total_venta': round(t_total, 2),
    }
    return {'datos': datos, 'totales': totales, 'periodo': periodo}


def generar_csv_libro(tipo_libro, resultado, empresa):
    """
    Genera CSV delimitado por punto y coma (;) replicando formato MH:
    - Consumidor: 23 columnas, sin encabezado (como VentaConsumidor.csv).
    - Contribuyentes: 20 columnas, sin encabezado (como VentaContribuyentes.csv).
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=';')
    datos = resultado['datos']
    totales = resultado['totales']
    periodo = resultado['periodo']
    if tipo_libro == 'consumidor':
        # 23 columnas: 5 = Nº Recepción (sello), 6-9 = Código generación (x4)
        for r in datos:
            sello = r.get('sello_recepcion', '') or ''
            codigo_gen = r.get('codigo_generacion', '') or ''
            writer.writerow([
                r['fecha_emision'],
                r.get('clase_raw', '4'),
                '01',
                r.get('numero_dte', r['numero_control']),
                sello,
                codigo_gen, codigo_gen, codigo_gen, codigo_gen,
                '',
                f"{r['ventas_exentas']:.2f}",
                '0.00',
                f"{r['ventas_no_sujetas']:.2f}",
                f"{r['ventas_internas_gravadas']:.2f}",
                '0.00', '0.00', '0.00', '0', '0',
                f"{r['total_ventas']:.2f}",
                r.get('clasificacion_venta', '1'),
                r.get('tipo_ingreso', '2'),
                '2',
            ])
    else:
        # 20 columnas: 5 = Nº Recepción (sello), 6 = Código generación
        for r in datos:
            sello = r.get('sello_recepcion', '') or ''
            codigo_gen = r.get('codigo_generacion', '') or ''
            writer.writerow([
                r['fecha_emision'],
                r.get('clase_raw', '4'),
                '03',
                r.get('numero_dte', r['numero_control']),
                sello,
                codigo_gen,
                '',
                r['nrc_cliente'],
                (r['nombre_cliente'] or '').replace(';', ''),
                '0.00', '0.00',
                f"{r['monto_neto']:.2f}",
                f"{r['debito_fiscal']:.2f}",
                '0', '0',
                f"{r['total_venta']:.2f}",
                '',
                r.get('clasificacion_venta', '1'),
                r.get('tipo_ingreso', '2'),
                '1',
            ])
    sufijo = 'CF' if tipo_libro == 'consumidor' else 'CCF'
    response = HttpResponse(buffer.getvalue(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="LIBRO_VENTAS_{sufijo}_{empresa.nombre}_{periodo}.csv"'
    return response


def generar_pdf_libro(tipo_libro, resultado, empresa):
    """Genera PDF del libro en orientación horizontal (landscape)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    buffer = io.BytesIO()
    datos = resultado['datos']
    totales = resultado['totales']
    periodo = resultado['periodo']
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(letter),
        rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=20,
    )
    elements = []
    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle(name='Titulo', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=14, spaceAfter=4)
    sub_style = ParagraphStyle(name='Sub', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10)
    if tipo_libro == 'consumidor':
        elements.append(Paragraph('LIBRO DE VENTAS A CONSUMIDOR FINAL', titulo_style))
    else:
        elements.append(Paragraph('LIBRO DE VENTAS A CONTRIBUYENTES', titulo_style))
    elements.append(Paragraph(f'MES DE {periodo}  |  {empresa.nombre}', sub_style))
    elements.append(Paragraph(f'NRC: {empresa.nrc}  |  NIT: {empresa.nit or "N/A"}', sub_style))
    elements.append(Spacer(1, 12))
    estilo_celda = ParagraphStyle(name='CeldaPDF', fontSize=6, leading=7, alignment=TA_LEFT)
    if tipo_libro == 'consumidor':
        headers = [
            'Fecha', 'Clase', 'Tipo', 'Nº Generación', 'Nº Recepción',
            'Exentas', 'Gravadas', 'No Sujetas', 'Total',
        ]
        col_widths = [48, 32, 24, 88, 88, 44, 44, 44, 48]
        rows = [headers]
        for r in datos:
            codigo = (r.get('codigo_generacion') or '')[:36]
            sello = (r.get('sello_recepcion') or '')[:36]
            rows.append([
                r['fecha_emision'], r.get('clase_raw', r['clase_documento']), r['tipo_documento'],
                Paragraph(codigo, estilo_celda) if codigo else '', Paragraph(sello, estilo_celda) if sello else '',
                f"{r['ventas_exentas']:,.2f}", f"{r['ventas_internas_gravadas']:,.2f}",
                f"{r['ventas_no_sujetas']:,.2f}", f"{r['total_ventas']:,.2f}",
            ])
        rows.append([
            '', '', '', '', 'TOTALES',
            f"{totales['ventas_exentas']:,.2f}", f"{totales['ventas_internas_gravadas']:,.2f}",
            f"{totales['ventas_no_sujetas']:,.2f}", f"{totales['total_ventas']:,.2f}",
        ])
    else:
        headers = ['Fecha', 'Nº Generación', 'Nº Recepción', 'NRC', 'Nombre Cliente', 'Monto Neto', 'Débito Fiscal', 'Total']
        col_widths = [48, 92, 92, 58, 95, 50, 52, 50]
        rows = [headers]
        for r in datos:
            codigo = (r.get('codigo_generacion') or '')[:40]
            sello = (r.get('sello_recepcion') or '')[:40]
            rows.append([
                r['fecha_emision'],
                Paragraph(codigo, estilo_celda) if codigo else '', Paragraph(sello, estilo_celda) if sello else '',
                (r['nrc_cliente'] or '')[:14], (r['nombre_cliente'] or '')[:22],
                f"{r['monto_neto']:,.2f}", f"{r['debito_fiscal']:,.2f}", f"{r['total_venta']:,.2f}",
            ])
        rows.append([
            '', '', '', '', 'TOTALES',
            f"{totales['monto_neto']:,.2f}", f"{totales['debito_fiscal']:,.2f}", f"{totales['total_venta']:,.2f}",
        ])
    tabla = Table(rows, colWidths=col_widths, repeatRows=1)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E5E7EB')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (5, 1), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E8E8E8')),
    ]))
    elements.append(tabla)
    doc.build(elements)
    buffer.seek(0)
    sufijo = 'CF' if tipo_libro == 'consumidor' else 'CCF'
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="LIBRO_VENTAS_{sufijo}_{empresa.nombre}_{periodo}.pdf"'
    return response
