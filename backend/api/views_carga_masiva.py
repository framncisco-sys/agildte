# -*- coding: utf-8 -*-
"""
Vistas para Carga Masiva de Facturas.
- POST /api/carga-masiva/upload/: recibe Excel/CSV, valida y devuelve filas parseadas
- GET /api/carga-masiva/plantilla-ejemplo/: descarga plantilla Excel de ejemplo
"""
import io
from decimal import Decimal
from datetime import datetime

import pandas as pd
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from django.db.models import Q

from .models import Cliente, Producto
from .utils.tenant import get_empresa_ids_allowlist, require_empresa_allowed


def _limpiar_nrc(val):
    if not val:
        return ""
    return str(val).replace("-", "").replace(" ", "").strip()


def _extraer_tipo_dte(val):
    """Extrae el código numérico del tipo DTE: '01', '01-CF', '03', '03-CCF' -> '01' o '03'."""
    if not val or (isinstance(val, float) and pd.isna(val)):
        return ''
    s = str(val).strip().upper()
    if s.startswith('01'):
        return '01'
    if s.startswith('03'):
        return '03'
    return s[:2] if len(s) >= 2 else s


# Columnas requeridas: al menos item 1
# 'nrc' es el NRC del cliente (para CCF) o 'CF' (para CF). Alias: 'cliente' para compatibilidad.
COLUMNAS_REQUERIDAS = ['cliente', 'tipo_dte', 'producto', 'cantidad', 'precio_unitario']
COLUMNAS_OPCIONALES = [
    'nombre_receptor', 'nombre_comercial', 'nit', 'documento_receptor', 'direccion', 'correo', 'fecha',
    'producto_2', 'cantidad_2', 'precio_2', 'producto_3', 'cantidad_3', 'precio_3',
    'cod_actividad', 'desc_actividad', 'departamento', 'municipio', 'telefono',
]

# Aliases para columnas. La columna NRC del cliente puede llamarse 'nrc', 'cliente' o 'nrc_cliente'.
ALIASES = {
    # NRC del cliente → columna interna 'cliente'
    'nrc': 'cliente',
    'nrc_cliente': 'cliente',
    'cliente': 'cliente',
    # NIT/DUI del contribuyente → columna interna 'nit'
    'nit': 'nit',
    'nit_cliente': 'nit',
    'dui': 'nit',
    'identificacion': 'nit',
    # Tipo DTE
    'tipo': 'tipo_dte',
    'tipo_documento': 'tipo_dte',
    'tipo_dte': 'tipo_dte',
    # Productos
    'descripcion': 'producto',
    'descripcion_producto': 'producto',
    'descripcion_item': 'producto',
    'codigo': 'producto',
    'codigo_producto': 'producto',
    'codigo_item': 'producto',
    'producto_servicio': 'producto',
    'producto': 'producto',
    # Cantidades y precios
    'cant': 'cantidad',
    'cantidad': 'cantidad',
    'precio': 'precio_unitario',
    'precio_unit': 'precio_unitario',
    'precio_unitario': 'precio_unitario',
    # Datos del receptor
    'nombre': 'nombre_receptor',
    'nombre_receptor': 'nombre_receptor',
    'nombre_comercial': 'nombre_comercial',
    'razon_social': 'nombre_receptor',
    'documento': 'documento_receptor',
    'documento_receptor': 'documento_receptor',
    'dir': 'direccion',
    'direccion': 'direccion',
    'email': 'correo',
    'correo': 'correo',
    'fecha': 'fecha',
    'fecha_emision': 'fecha',
    'cod_actividad': 'cod_actividad',
    'cod_actividad_receptor': 'cod_actividad',
    'desc_actividad': 'desc_actividad',
    'desc_actividad_receptor': 'desc_actividad',
    'departamento': 'departamento',
    'municipio': 'municipio',
    'telefono': 'telefono',
    'tel': 'telefono',
}


def _normalizar_columnas(df):
    """Normaliza nombres de columnas (lowercase, sin espacios, aplica aliases).
    Compatible con plantillas tipo 'tributarios v1' (NIT, NRC, Tipo Documento, etc.).
    """
    cols = {}
    for c in df.columns:
        key = str(c).lower().strip().replace(' ', '_').replace('.', '_')
        key = ALIASES.get(key, key)
        if key in COLUMNAS_REQUERIDAS or key in COLUMNAS_OPCIONALES:
            cols[c] = key
    return df.rename(columns=cols)


def _parse_item(row, suffix):
    """Extrae un ítem de la fila. suffix='' para item 1, '_2' para item 2, '_3' para item 3."""
    prod = str(row.get('producto' + suffix, '') or '').strip() if pd.notna(row.get('producto' + suffix, '')) else ''
    if not prod:
        return None
    try:
        cant = float(Decimal(str(row.get('cantidad' + suffix, 0) or 0).replace(',', '.')))
        if cant <= 0:
            return None
    except (ValueError, TypeError):
        return None
    try:
        prec_val = row.get('precio_unitario' + suffix) or row.get('precio' + suffix) or 0
        prec = float(Decimal(str(prec_val).replace(',', '.')))
        if prec < 0:
            prec = 0.0
    except (ValueError, TypeError):
        prec = 0.0
    return {'producto': prod, 'cantidad': cant, 'precio_unitario': prec}


def _validar_fila(row, idx, empresa_id):
    """Valida una fila y devuelve (datos_ok, errores). Soporta 1 a 3 ítems por factura."""
    errores = []
    datos = {}

    # Cliente (NRC o "CF")
    cliente_raw = str(row.get('cliente', '')).strip() if pd.notna(row.get('cliente')) else ''
    if not cliente_raw:
        errores.append('Cliente/NRC es requerido')
    else:
        datos['cliente'] = cliente_raw

    # Tipo DTE (acepta '01', '01-CF', '03', '03-CCF')
    tipo_raw = str(row.get('tipo_dte', '')).strip() if pd.notna(row.get('tipo_dte')) else ''
    tipo = _extraer_tipo_dte(tipo_raw) if tipo_raw else ''
    if tipo not in ('01', '03'):
        errores.append('Tipo DTE debe ser 01 (Consumidor Final) o 03 (Crédito Fiscal)')
    else:
        datos['tipo_dte'] = tipo

    # Ítems (1 a 3): producto, cantidad, precio_unitario [+ _2, _3]
    items = []
    for suf in ['', '_2', '_3']:
        it = _parse_item(row, suf)
        if it:
            items.append(it)
    if not items:
        it1 = _parse_item(row, '')
        if not it1:
            prod = str(row.get('producto', '') or '').strip()
            if not prod:
                errores.append('Al menos un producto/descripción es requerido')
            else:
                try:
                    cant = float(Decimal(str(row.get('cantidad', 0) or 0).replace(',', '.')))
                    prec = float(Decimal(str(row.get('precio_unitario', 0) or row.get('precio', 0) or 0).replace(',', '.')))
                    items = [{'producto': prod, 'cantidad': max(0.01, cant), 'precio_unitario': max(0, prec)}]
                except (ValueError, TypeError):
                    errores.append('Cantidad y precio unitario inválidos')
        else:
            items = [it1]
    datos['items'] = items

    # Compatibilidad: producto/cantidad/precio para item 1
    datos['producto'] = items[0]['producto'] if items else ''
    datos['cantidad'] = items[0]['cantidad'] if items else 1.0
    datos['precio_unitario'] = items[0]['precio_unitario'] if items else 0.0

    # Opcionales. Para CF (01): si documento_receptor vacío, usar nombre 'Consumidor Final'
    datos['nombre_receptor'] = str(row.get('nombre_receptor', '')).strip() or None
    datos['nombre_comercial'] = str(row.get('nombre_comercial', '')).strip() or None
    # Normalizar NIT/DUI: Excel elimina ceros iniciales.
    # 8 dígitos → DUI sin cero → completar a 9. 13 dígitos → NIT sin cero → completar a 14.
    _nit_raw = str(row.get('nit', '') or '').strip()
    _nit_dig = ''.join(c for c in _nit_raw.replace('-', '').replace(' ', '') if c.isdigit())
    if len(_nit_dig) == 8:
        _nit_dig = '0' + _nit_dig   # DUI: Excel quitó el cero inicial
    elif len(_nit_dig) == 13:
        _nit_dig = '0' + _nit_dig   # NIT: Excel quitó el cero inicial
    elif len(_nit_dig) == 10:
        _nit_dig = _nit_dig[:9]     # DUI con dígito extra, recortar
    datos['nit'] = _nit_dig if _nit_dig else None
    doc_rep = str(row.get('documento_receptor', '')).strip() or None
    if datos.get('tipo_dte') == '01' and not doc_rep:
        datos['nombre_receptor'] = datos['nombre_receptor'] or 'Consumidor Final'
        datos['documento_receptor'] = ''
    else:
        datos['documento_receptor'] = doc_rep
    datos['direccion'] = str(row.get('direccion', '')).strip() or None
    datos['correo'] = str(row.get('correo', '')).strip() or None
    datos['cod_actividad'] = str(row.get('cod_actividad', '')).strip() or None
    datos['desc_actividad'] = str(row.get('desc_actividad', '')).strip() or None
    datos['departamento'] = str(row.get('departamento', '')).strip() or None
    datos['municipio'] = str(row.get('municipio', '')).strip() or None
    datos['telefono'] = str(row.get('telefono', '')).strip() or None
    fecha_raw = row.get('fecha')
    if pd.notna(fecha_raw) and fecha_raw:
        try:
            if isinstance(fecha_raw, datetime):
                datos['fecha'] = fecha_raw.strftime('%Y-%m-%d')
            else:
                d = pd.to_datetime(fecha_raw)
                datos['fecha'] = d.strftime('%Y-%m-%d')
        except Exception:
            datos['fecha'] = None
    else:
        datos['fecha'] = None

    # Validación adicional: CCF requiere NRC y NIT/DUI (identificación del contribuyente)
    # Ley de homologación: CCF puede tener DUI (9 dígitos) o NIT (14 dígitos). Detección automática.
    if datos.get('tipo_dte') == '03':
        if datos.get('cliente', '').upper() in ('CF', 'CONSUMIDOR FINAL', ''):
            errores.append('Crédito Fiscal (03) requiere NRC del cliente en columna "cliente"')
        doc_val = (datos.get('nit') or '').strip()
        if not doc_val:
            errores.append('Crédito Fiscal (03) requiere NIT o DUI en columna "nit". DUI=9 dígitos, NIT=14 dígitos.')

    datos['_fila'] = idx + 1
    datos['_errores'] = errores
    return datos


def _crear_plantilla_ejemplo():
    """Genera plantilla completa con todos los datos del receptor e ítems (hasta 3 por factura).
    Columna nit/dui: acepta NIT (14 dígitos) o DUI (9 dígitos). Detección automática (ley de homologación).
    """
    data = [
        # CCF (03): nombre_receptor, nombre_comercial, nit, nrc, tipo_dte, cod_actividad, ...
        [
            'L&K SOCIEDAD ANONIMA', 'L&K Comercial', '0614-120589-102-4', '120589-4', '03',
            '10005', 'Comercio al por menor', 'Col. Escalón, San Salvador', '06', '14',
            'cliente@empresa.com', '22222222',
            'Servicio de consultoría', 1, 500.00,
            'Producto adicional', 2, 25.00,
            '', 0, 0,
            '',
        ],
        # CF (01): nrc = CF, nit vacío
        [
            'Consumidor Final', '', '', 'CF', '01',
            '', '', 'San Salvador', '', '',
            '', '',
            'Producto genérico', 2, 10.50,
            'Otro item', 1, 5.00,
            '', 0, 0,
            '',
        ],
    ]
    cols = [
        'nombre_receptor', 'nombre_comercial', 'nit', 'nrc', 'tipo_dte',
        'cod_actividad', 'desc_actividad', 'direccion', 'departamento', 'municipio',
        'correo', 'telefono',
        'producto', 'cantidad', 'precio_unitario',
        'producto_2', 'cantidad_2', 'precio_2',
        'producto_3', 'cantidad_3', 'precio_3',
        'fecha',
    ]
    return pd.DataFrame(data, columns=cols)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def carga_masiva_upload(request):
    """
    Recibe archivo .xlsx o .csv con filas de facturas.
    Valida cada fila y devuelve datos parseados para revisión en el frontend.
    Body: multipart/form-data con 'archivo' y 'empresa_id'
    """
    empresa_ids = get_empresa_ids_allowlist(request)
    if not empresa_ids:
        return Response({"detail": "Autenticación requerida"}, status=status.HTTP_401_UNAUTHORIZED)

    empresa_id = request.data.get('empresa_id') or request.query_params.get('empresa_id')
    if not empresa_id:
        return Response({"detail": "empresa_id es requerido"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        empresa_id = int(empresa_id)
    except (TypeError, ValueError):
        return Response({"detail": "empresa_id debe ser un número"}, status=status.HTTP_400_BAD_REQUEST)

    r = require_empresa_allowed(request, empresa_id)
    if r is not None:
        return r

    archivo = request.FILES.get('archivo')
    if not archivo:
        return Response({"detail": "Se requiere el archivo 'archivo'"}, status=status.HTTP_400_BAD_REQUEST)

    nombre = (archivo.name or '').lower()
    if not (nombre.endswith('.xlsx') or nombre.endswith('.xls') or nombre.endswith('.csv')):
        return Response({
            "detail": "Formato no soportado. Use .xlsx, .xls o .csv"
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        content = archivo.read()
        if nombre.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content), encoding='utf-8-sig')
        else:
            df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        return Response({
            "detail": f"No se pudo leer el archivo: {str(e)}"
        }, status=status.HTTP_400_BAD_REQUEST)

    if df.empty:
        return Response({"detail": "El archivo está vacío"}, status=status.HTTP_400_BAD_REQUEST)

    df = _normalizar_columnas(df)
    faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in df.columns]
    if faltantes:
        return Response({
            "detail": f"Faltan columnas requeridas: {', '.join(faltantes)}. Use la plantilla de ejemplo."
        }, status=status.HTTP_400_BAD_REQUEST)

    filas = []
    for idx, row in df.iterrows():
        datos = _validar_fila(row, idx, empresa_id)
        # Resolver cliente_id y producto_id para facilitar emisión
        if not datos['_errores']:
            if datos['tipo_dte'] == '03' and datos.get('cliente'):
                cliente_obj = Cliente.objects.filter(
                    empresa_id=empresa_id
                ).filter(
                    Q(nrc__iexact=_limpiar_nrc(datos['cliente'])) |
                    Q(nit__iexact=_limpiar_nrc(datos['cliente']))
                ).first()
                datos['cliente_id'] = cliente_obj.id if cliente_obj else None
            else:
                datos['cliente_id'] = None
            for item in datos.get('items', []):
                prod_str = (item.get('producto') or '').strip()
                prod_obj = None
                if prod_str:
                    prod_obj = Producto.objects.filter(
                        empresa_id=empresa_id, activo=True, codigo__iexact=prod_str
                    ).first()
                if not prod_obj and prod_str:
                    prod_obj = Producto.objects.filter(
                        empresa_id=empresa_id, activo=True
                    ).filter(Q(descripcion__iexact=prod_str) | Q(descripcion__icontains=prod_str)).first()
                if not prod_obj and prod_str:
                    try:
                        import uuid
                        precio = Decimal(str(item.get('precio_unitario', 0)))
                        codigo_safe = (prod_str[:40].replace('/', '-').replace('\\', '-') or 'ITEM') + '-' + str(uuid.uuid4())[:6].upper()
                        prod_obj = Producto.objects.create(
                            empresa_id=empresa_id,
                            codigo=codigo_safe[:50],
                            descripcion=prod_str[:200],
                            precio_unitario=precio,
                        )
                    except Exception:
                        pass
                item['producto_id'] = prod_obj.id if prod_obj else None
                item['_producto_reconocido'] = prod_obj is not None
        if datos.get('items'):
            datos['producto_id'] = datos['items'][0].get('producto_id')
            datos['_producto_reconocido'] = datos['items'][0].get('_producto_reconocido', True)
        filas.append(datos)

    return Response({
        "filas": filas,
        "total": len(filas),
        "empresa_id": empresa_id,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def carga_masiva_plantilla_ejemplo(request):
    """Descarga una plantilla Excel de ejemplo para carga masiva."""
    df = _crear_plantilla_ejemplo()
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Facturas', index=False)
    output.seek(0)
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="plantilla_carga_masiva.xlsx"'
    return response
