import json
import csv
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum
from .models import Cliente, Compra, Venta, Retencion
from .serializers import ClienteSerializer, CompraSerializer, VentaSerializer, RetencionSerializer

# --- UTILIDADES ---
def safe_float(val):
    try: return float(val) if val else 0.0
    except: return 0.0

def limpiar(valor):
    if not valor: return ""
    return str(valor).replace("-", "").replace(" ", "").strip()

# --- CLIENTES ---
# --- CLIENTES (UNIFICADO) ---
@api_view(['GET', 'POST'])
def clientes_api(request):
    if request.method == 'GET':
        # Lógica de listar
        clientes = Cliente.objects.all()
        serializer = ClienteSerializer(clientes, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Lógica de crear
        serializer = ClienteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
# --- CARGA MASIVA ---
@api_view(['POST'])
def procesar_lote_dtes(request):
    cliente_nrc = request.data.get('nrc_activo')
    archivos = request.FILES.getlist('archivos')
    if not cliente_nrc: return Response({"error": "Sin cliente"}, status=400)
    
    mi_nrc = limpiar(cliente_nrc)
    reporte = { "compras": [], "ventas": [], "retenciones": [], "ignorados": [], "resumen": {"total_iva_compras": 0, "total_iva_ventas": 0} }

    for archivo in archivos:
        try:
            contenido = json.load(archivo)
            ident = contenido.get('identificacion', {})
            tipo_dte = ident.get('tipoDte')
            codigo = str(ident.get('codigoGeneracion', '')).strip()
            num_control = ident.get('numeroControl', '')
            fecha = ident.get('fecEmi')
            sello = ident.get('selloRecibido') or contenido.get('selloRecibido')
            
            emisor = contenido.get('emisor', {})
            receptor = contenido.get('receptor') or {}
            cuerpo = contenido.get('resumen', {})
            
            nrc_emis = limpiar(emisor.get('nrc'))
            nrc_recep = limpiar(receptor.get('nrc'))
            soy_emisor = (nrc_emis == mi_nrc)
            soy_receptor = (nrc_recep == mi_nrc)

            if not soy_emisor and not soy_receptor:
                reporte["ignorados"].append({"archivo": archivo.name, "motivo": f"NRC Ajeno ({nrc_emis} vs {nrc_recep})"})
                continue 

            gravado = safe_float(cuerpo.get('totalGravada'))
            iva = safe_float(cuerpo.get('totalIva'))
            total = safe_float(cuerpo.get('totalPagar'))
            percepcion = safe_float(cuerpo.get('totalIvaPercibido')) # <--- PERCEPCIÓN

            if iva == 0 and tipo_dte != '14':
                tributos = cuerpo.get('tributos') or []
                if not tributos and 'cuerpoDocumento' in contenido:
                     for item in contenido['cuerpoDocumento']: iva += safe_float(item.get('ivaItem'))
                else:
                    for t in tributos:
                        if t.get('codigo') == '20': iva += safe_float(t.get('valor'))

            if soy_receptor: # COMPRA
                if tipo_dte == '03' or tipo_dte == '14': 
                    existe = Compra.objects.filter(cliente__nrc=cliente_nrc, codigo_generacion=codigo).exists()
                    estado = "Duplicado" if existe else "Nuevo"
                    item = { "archivo": archivo.name, "codigo": codigo, "fecha": fecha, "tipo_dte": tipo_dte, "emisor_nombre": emisor.get('nombre'), "emisor_nrc": emisor.get('nrc'), "gravado": gravado, "iva": iva, "percepcion": percepcion, "total": total, "sello": sello, "clasificacion_1": "Gravada", "clasificacion_2": "Gasto", "estado_validacion": estado }
                    if estado == "Duplicado": reporte["ignorados"].append({"archivo": archivo.name, "motivo": "Ya registrada"})
                    else: 
                        reporte["compras"].append(item)
                        reporte["resumen"]["total_iva_compras"] += iva
                elif tipo_dte == '07':
                    item = { "archivo": archivo.name, "codigo": codigo, "fecha": fecha, "tipo_dte": tipo_dte, "emisor_nombre": emisor.get('nombre'), "emisor_nrc": emisor.get('nit'), "monto_sujeto": safe_float(cuerpo.get('totalSujetoRetencion')), "monto_retenido": safe_float(cuerpo.get('totalIVAretenido')), "sello": sello }
                    reporte["retenciones"].append(item)

            elif soy_emisor: # VENTA
                if tipo_dte in ['01', '03']:
                    existe = Venta.objects.filter(cliente__nrc=cliente_nrc, numero_documento=codigo).exists()
                    estado = "Duplicado" if existe else "Nuevo"
                    if tipo_dte == '01' and iva == 0 and gravado > 0:
                         real_gravado = gravado / 1.13; iva = gravado - real_gravado; gravado = real_gravado
                    item = { "archivo": archivo.name, "codigo": codigo, "num_control": num_control, "fecha": fecha, "tipo_dte": tipo_dte, "receptor_nombre": receptor.get('nombre') or "Consumidor Final", "receptor_nrc": receptor.get('nrc'), "gravado": gravado, "iva": iva, "total": total, "sello": sello, "clasificacion_venta": "1", "tipo_ingreso": "3", "estado_validacion": estado }
                    if estado == "Duplicado": reporte["ignorados"].append({"archivo": archivo.name, "motivo": "Ya registrada"})
                    else:
                        reporte["ventas"].append(item)
                        reporte["resumen"]["total_iva_ventas"] += iva

        except Exception as e:
            reporte["ignorados"].append({"archivo": archivo.name, "motivo": f"Error: {str(e)}"})
    return Response(reporte)

@api_view(['POST'])
def guardar_lote_aprobado(request):
    data = request.data
    cliente_nrc = data.get('nrc_activo')
    try: cliente_obj = Cliente.objects.get(nrc=cliente_nrc)
    except: return Response({"error": "Cliente no existe"}, status=404)
    res = {"compras": 0, "ventas": 0, "retenciones": 0, "duplicados": 0}

    for c in data.get('compras', []):
        if not Compra.objects.filter(cliente=cliente_obj, codigo_generacion=c['codigo']).exists():
            Compra.objects.create(cliente=cliente_obj, fecha_emision=c['fecha'], tipo_documento=c['tipo_dte'], codigo_generacion=c['codigo'], nrc_proveedor=c['emisor_nrc'], nombre_proveedor=c['emisor_nombre'], monto_gravado=c['gravado'], monto_iva=c['iva'], monto_percepcion=c.get('percepcion', 0), monto_total=c['total'], periodo_aplicado=c['fecha'][:7], estado="Registrado", clasificacion_1=c.get('clasificacion_1', 'Gravada'), clasificacion_2=c.get('clasificacion_2', 'Gasto'))
            res["compras"] += 1
        else: res["duplicados"] += 1

    for v in data.get('ventas', []):
        if not Venta.objects.filter(cliente=cliente_obj, numero_documento=v['codigo']).exists():
            tipo = 'CCF' if v['tipo_dte'] == '03' else 'CF'
            Venta.objects.create(cliente=cliente_obj, fecha_emision=v['fecha'], periodo_aplicado=v['fecha'][:7], tipo_venta=tipo, clase_documento='4', numero_documento=v['codigo'], numero_control=v.get('num_control'), sello_recepcion=v.get('sello'), nombre_receptor=v.get('receptor_nombre'), nrc_receptor=v.get('receptor_nrc'), venta_gravada=v.get('gravado',0), debito_fiscal=v.get('iva',0), clasificacion_venta=v.get('clasificacion_venta', '1'), tipo_ingreso=v.get('tipo_ingreso', '3'))
            res["ventas"] += 1
        else: res["duplicados"] += 1

    for r in data.get('retenciones', []):
        if not Retencion.objects.filter(cliente=cliente_obj, codigo_generacion=r['codigo']).exists():
            Retencion.objects.create(cliente=cliente_obj, fecha_emision=r['fecha'], periodo_aplicado=r['fecha'][:7], tipo_retencion='162', codigo_generacion=r['codigo'], sello_recepcion=r.get('sello'), nombre_emisor=r.get('emisor_nombre'), nit_emisor=r.get('nit_emisor') or "", monto_sujeto=r.get('monto_sujeto', 0), monto_retenido=r.get('monto_retenido', 0))
            res["retenciones"] += 1
        else: res["duplicados"] += 1
    return Response({"status": "ok", "resumen": res})

# --- CRUD INDIVIDUAL ---
@api_view(['POST'])
def crear_compra(request):
    serializer = CompraSerializer(data=request.data)
    if serializer.is_valid(): serializer.save(); return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)
@api_view(['GET'])
def listar_compras(request):
    cliente_id = request.query_params.get('nrc'); periodo = request.query_params.get('periodo')
    compras = Compra.objects.filter(cliente__nrc=cliente_id, periodo_aplicado=periodo).order_by('fecha_emision')
    serializer = CompraSerializer(compras, many=True); return Response(serializer.data)
@api_view(['DELETE'])
def borrar_compra(request, pk):
    try: Compra.objects.get(pk=pk).delete(); return Response(status=204)
    except: return Response(status=404)
@api_view(['PUT'])
def actualizar_compra(request, pk):
    try: compra = Compra.objects.get(pk=pk)
    except: return Response(status=404)
    serializer = CompraSerializer(compra, data=request.data); 
    if serializer.is_valid(): serializer.save(); return Response(serializer.data)
    return Response(serializer.errors, status=400)
@api_view(['POST'])
def crear_venta(request):
    serializer = VentaSerializer(data=request.data); 
    if serializer.is_valid(): serializer.save(); return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)
@api_view(['GET'])
def listar_ventas(request):
    cliente_id = request.query_params.get('nrc'); periodo = request.query_params.get('periodo'); tipo = request.query_params.get('tipo')
    ventas = Venta.objects.filter(cliente__nrc=cliente_id, periodo_aplicado=periodo)
    if tipo: ventas = ventas.filter(tipo_venta=tipo)
    serializer = VentaSerializer(ventas.order_by('fecha_emision'), many=True); return Response(serializer.data)
@api_view(['DELETE'])
def borrar_venta(request, pk):
    try: Venta.objects.get(pk=pk).delete(); return Response(status=204)
    except: return Response(status=404)
@api_view(['POST'])
def crear_retencion(request):
    serializer = RetencionSerializer(data=request.data)
    if serializer.is_valid(): serializer.save(); return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)
@api_view(['GET'])
def listar_retenciones(request):
    cliente_id = request.query_params.get('nrc'); periodo = request.query_params.get('periodo')
    rets = Retencion.objects.filter(cliente__nrc=cliente_id, periodo_aplicado=periodo).order_by('fecha_emision')
    serializer = RetencionSerializer(rets, many=True); return Response(serializer.data)

# --- FINANZAS ---
@api_view(['GET'])
def resumen_fiscal(request):
    cliente_id = request.query_params.get('nrc'); periodo = request.query_params.get('periodo')
    compras = Compra.objects.filter(cliente__nrc=cliente_id, periodo_aplicado=periodo)
    s_comp = compras.aggregate(Sum('monto_gravado'))['monto_gravado__sum'] or 0
    s_cred = compras.aggregate(Sum('monto_iva'))['monto_iva__sum'] or 0
    s_perc = compras.aggregate(Sum('monto_percepcion'))['monto_percepcion__sum'] or 0 # <--- PERCEPCIÓN SUMADA
    ventas = Venta.objects.filter(cliente__nrc=cliente_id, periodo_aplicado=periodo)
    s_vent = ventas.aggregate(Sum('venta_gravada'))['venta_gravada__sum'] or 0
    s_deb = ventas.aggregate(Sum('debito_fiscal'))['debito_fiscal__sum'] or 0
    rets = Retencion.objects.filter(cliente__nrc=cliente_id, periodo_aplicado=periodo)
    s_ret1 = rets.filter(tipo_retencion='162').aggregate(Sum('monto_retenido'))['monto_retenido__sum'] or 0
    s_ret2 = rets.filter(tipo_retencion='161').aggregate(Sum('monto_retenido'))['monto_retenido__sum'] or 0
    return Response({ "ventasGravadas": s_vent, "debitoFiscal": s_deb, "comprasGravadas": s_comp, "creditoFiscal": s_cred, "percepcionesPagadas": s_perc, "retencionCliente1": s_ret1, "retencionTarjeta2": s_ret2 })

# --- CSV ---
@api_view(['GET'])
def generar_csv_163(request):
    cliente_id = request.query_params.get('nrc'); periodo = request.query_params.get('periodo')
    response = HttpResponse(content_type='text/csv'); response['Content-Disposition'] = f'attachment; filename="ANEXO_163_{periodo}.csv"'
    writer = csv.writer(response, delimiter=';')
    compras = Compra.objects.filter(cliente__nrc=cliente_id, periodo_aplicado=periodo, monto_percepcion__gt=0)
    for c in compras:
        fecha = c.fecha_emision.strftime("%d/%m/%Y")
        fila = ["", fecha, c.codigo_generacion, "SERIE", format(c.monto_gravado+c.monto_iva, '.2f'), format(c.monto_percepcion, '.2f'), "0.00", "10"]
        writer.writerow(fila)
    return response

# ==========================================
# 7. REPORTES CSV (FÁBRICA DE ANEXOS MH)
# ==========================================

@api_view(['GET'])
def generar_csv_compras(request):
    cliente_id = request.query_params.get('nrc')
    periodo = request.query_params.get('periodo')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="COMPRAS_{periodo}.csv"'
    writer = csv.writer(response, delimiter=';')
    compras = Compra.objects.filter(cliente__nrc=cliente_id, periodo_aplicado=periodo).order_by('fecha_emision')
    map_clasif_1 = {"Gravada": "1", "Exenta": "2", "No Sujeta": "3"}
    map_clasif_2 = {"Costo": "1", "Gasto": "2"}
    map_clasif_3 = { "Industria": "1", "Comercio": "2", "Servicios": "3", "Agropecuario": "4", "Administración": "1", "Ventas": "2", "Financiero": "3" }

    for c in compras:
        fecha_fmt = c.fecha_emision.strftime("%d/%m/%Y")
        clase_doc = "4" if c.codigo_generacion and len(str(c.codigo_generacion)) > 20 else "1"
        tipo_doc = c.tipo_documento.zfill(2)
        nombre_limpio = c.nombre_proveedor.replace(";", "") if c.nombre_proveedor else ""
        es_importacion = c.tipo_documento == '12'
        col_9_internas = format(c.monto_gravado, '.2f') if not es_importacion else "0.00"
        col_8_import = format(c.monto_gravado, '.2f') if es_importacion else "0.00"
        cod_1 = map_clasif_1.get(c.clasificacion_1, "1")
        cod_2 = map_clasif_2.get(c.clasificacion_2, "1")
        cod_3 = map_clasif_3.get(c.clasificacion_3, "1")
        
        fila = [
            fecha_fmt, clase_doc, tipo_doc, c.codigo_generacion, c.nrc_proveedor, nombre_limpio,
            "0.00", "0.00", col_8_import, col_9_internas, "0.00", "0.00", "0.00",
            format(c.monto_iva, '.2f'), format(c.monto_total, '.2f'), "", cod_1, cod_2, cod_3, "5", "3"
        ]
        writer.writerow(fila)
    return response

@api_view(['GET'])
def generar_csv_ventas_ccf(request):
    cliente_id = request.query_params.get('nrc')
    periodo = request.query_params.get('periodo')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="VENTAS_CCF_{periodo}.csv"'
    writer = csv.writer(response, delimiter=';')
    ventas = Venta.objects.filter(cliente__nrc=cliente_id, periodo_aplicado=periodo, tipo_venta='CCF').order_by('fecha_emision')

    for v in ventas:
        fecha_fmt = v.fecha_emision.strftime("%d/%m/%Y")
        clase_doc = v.clase_documento
        tipo_doc = "03"
        resolucion = v.numero_resolucion if clase_doc != '4' else ""
        serie = v.serie_documento if clase_doc != '4' else ""
        num_prin = v.numero_documento.strip()
        num_sec = v.numero_formulario_unico.strip() if (clase_doc == '2' and v.numero_formulario_unico) else num_prin
        nombre_limpio = v.nombre_receptor.replace(";", "") if v.nombre_receptor else ""
        
        monto_exento = "0.00"
        monto_gravado = "0.00"
        monto_nosujeto = "0.00"
        base = v.venta_gravada
        
        if v.clasificacion_venta == "2": monto_exento = format(base, '.2f')
        elif v.clasificacion_venta == "3": monto_nosujeto = format(base, '.2f')
        else: monto_gravado = format(base, '.2f')

        fila = [
            fecha_fmt, clase_doc, tipo_doc, resolucion, serie, num_prin, num_sec,
            v.nrc_receptor, nombre_limpio, monto_exento, "0.00", monto_gravado, 
            format(v.debito_fiscal, '.2f'), monto_nosujeto, "0.00", format(v.venta_gravada + v.debito_fiscal, '.2f'),
            "", v.clasificacion_venta.zfill(2), v.tipo_ingreso.zfill(2), "1"
        ]
        writer.writerow(fila)
    return response

# 9. Generar CSV Ventas Consumidor Final (Anexo 2) - ¡MEJORADO!
# 9. Generar CSV Ventas Consumidor Final (Anexo 2) - ¡VERSIÓN FINAL CORREGIDA MH!
@api_view(['GET'])
def generar_csv_ventas_cf(request):
    cliente_id = request.query_params.get('nrc')
    periodo = request.query_params.get('periodo')
    
    response = HttpResponse(content_type='text/csv')
    nombre_archivo = f"VENTAS_CF_{periodo}.csv"
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'

    writer = csv.writer(response, delimiter=';')

    ventas = Venta.objects.filter(
        cliente__nrc=cliente_id, 
        periodo_aplicado=periodo,
        tipo_venta='CF'
    ).order_by('fecha_emision') # O por numero_control si prefieres

    for v in ventas:
        fecha_fmt = v.fecha_emision.strftime("%d/%m/%Y")
        clase_doc = v.clase_documento
        
        # 1. LIMPIEZA DE DATOS (Quitar guiones)
        cod_gen_limpio = str(v.codigo_generacion or "").replace("-", "").upper()
        num_ctrl_limpio = str(v.numero_control or "").replace("-", "").upper()
        sello_limpio = str(v.sello_recepcion or "").replace("-", "").upper()

        # 2. ASIGNACIÓN DE COLUMNAS SEGÚN CLASE
        # Si es DTE (4)
        if clase_doc == '4':
            tipo_doc_mh = "01"   # Col 2: MH usa '01' para Factura Electrónica en este anexo
            col_3_res = num_ctrl_limpio  # Col 3: Número de Control
            col_4_ser = sello_limpio     # Col 4: Sello
            
            # Col 5, 6, 7, 8: Código de Generación repetido
            col_5_ci_del = cod_gen_limpio
            col_6_ci_al = cod_gen_limpio
            col_7_del = cod_gen_limpio
            col_8_al = cod_gen_limpio
            
            col_9_maq = "" # Col 9: Vacío para DTE
            
        else: 
            # Si es Físico (1, 2, 3)
            tipo_doc_mh = "01" # O "10" para Tiquete, "2" para Factura física
            col_3_res = v.numero_resolucion or ""
            col_4_ser = v.serie_documento or ""
            col_5_ci_del = ""
            col_6_ci_al = ""
            col_7_del = v.numero_control_desde or v.numero_documento
            col_8_al = v.numero_control_hasta or v.numero_documento
            col_9_maq = "" # O número de máquina si es ticket

        # 3. MONTOS
        monto_exento = "0.00"
        monto_gravado = "0.00"
        
        # Para CF, el monto reportado suele ser el TOTAL de la venta (con IVA) o la Base.
        # En tu archivo correcto (64.0) parece ser la Venta Total.
        # Si tu base de datos tiene 'venta_gravada' como base, sumamos IVA.
        
        total_venta_dia = v.venta_gravada + v.debito_fiscal
        
        if v.clasificacion_venta == "2": # Exenta
             monto_exento = format(total_venta_dia, '.2f')
        else:
             # Si es gravada, en este anexo MH suele pedir el valor de la venta
             monto_gravado = format(v.venta_gravada, '.2f') # Probemos con la Base
             # Si MH rechaza, cambia esta línea por: format(total_venta_dia, '.2f')

        total_fmt = format(total_venta_dia, '.2f')

        # --- FILA DE 23 COLUMNAS (0 a 22) ---
        fila = [
            fecha_fmt,          # 0. Fecha
            clase_doc,          # 1. Clase (4)
            tipo_doc_mh,        # 2. Tipo (1)
            col_3_res,          # 3. Resolución / Num Control
            col_4_ser,          # 4. Serie / Sello
            col_5_ci_del,       # 5. Control Interno Del (CodGen)
            col_6_ci_al,        # 6. Control Interno Al (CodGen)
            col_7_del,          # 7. Del Numero (CodGen)
            col_8_al,           # 8. Al Numero (CodGen)
            col_9_maq,          # 9. Maquina
            monto_exento,       # 10. Exentas
            "0.00",             # 11. Int. Exentas No Sujetas
            "0.00",             # 12. No Sujetas
            monto_gravado,      # 13. Gravadas
            "0.00",             # 14. Exp Centroamérica
            "0.00",             # 15. Exp Fuera
            "0.00",             # 16. Exp Servicios
            "0.00",             # 17. Zonas Francas
            "0.00",             # 18. Terceros
            total_fmt,          # 19. Total
            v.clasificacion_venta, # 20. Tipo Op (1) - Sin ceros extra si tu ejemplo tiene 1
            v.tipo_ingreso,        # 21. Tipo Ing (2 o 3) - Sin ceros extra
            "2"                    # 22. Tipo Anexo
        ]
        writer.writerow(fila)

    return response

@api_view(['GET'])
def generar_csv_161(request):
    cliente_id = request.query_params.get('nrc')
    periodo = request.query_params.get('periodo')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="ANEXO_161_{periodo}.csv"'
    writer = csv.writer(response, delimiter=';')
    retenciones = Retencion.objects.filter(cliente__nrc=cliente_id, periodo_aplicado=periodo, tipo_retencion='161')
    for r in retenciones:
        fecha_fmt = r.fecha_emision.strftime("%d/%m/%Y")
        nit_limpio = r.nit_emisor.replace("-", "")
        fila = [nit_limpio, fecha_fmt, r.numero_documento, r.codigo_generacion or r.numero_serie, format(r.monto_sujeto, '.2f'), format(r.monto_retenido, '.2f'), "0.00", "6"]
        writer.writerow(fila)
    return response

@api_view(['GET'])
def generar_csv_162(request):
    cliente_id = request.query_params.get('nrc')
    periodo = request.query_params.get('periodo')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="ANEXO_162_{periodo}.csv"'
    writer = csv.writer(response, delimiter=';')
    retenciones = Retencion.objects.filter(cliente__nrc=cliente_id, periodo_aplicado=periodo, tipo_retencion='162')
    for r in retenciones:
        fecha_fmt = r.fecha_emision.strftime("%d/%m/%Y")
        nit_limpio = r.nit_emisor.replace("-", "")
        fila = [nit_limpio, fecha_fmt, "7", r.numero_serie or "SERIE", r.numero_documento, format(r.monto_sujeto, '.2f'), format(r.monto_retenido, '.2f'), "0.00", "7"]
        writer.writerow(fila)
    return response

# 10. PDF COMPRAS (CARTA / LETTER) - ¡ACTUALIZADO!
@api_view(['GET'])
def generar_pdf_compras(request):
    cliente_id = request.query_params.get('nrc')
    periodo = request.query_params.get('periodo')
    
    # CAMBIO 1: Importamos 'letter' en vez de 'legal'
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib import colors
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="LIBRO_COMPRAS_{periodo}.pdf"'

    try:
        cliente = Cliente.objects.get(nrc=cliente_id)
        compras = Compra.objects.filter(cliente=cliente, periodo_aplicado=periodo).order_by('fecha_emision')
    except Cliente.DoesNotExist:
        return HttpResponse("Cliente no encontrado", status=404)

    # CAMBIO 2: Usamos 'pagesize=landscape(letter)'
    doc = SimpleDocTemplate(response, pagesize=landscape(letter), rightMargin=15, leftMargin=15, topMargin=30, bottomMargin=20)
    elements = []
    styles = getSampleStyleSheet()

    # Encabezado
    estilo_titulo = ParagraphStyle(name='Titulo', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=14, spaceAfter=2)
    estilo_sub = ParagraphStyle(name='Sub', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10)

    elements.append(Paragraph("LIBRO DE COMPRAS", estilo_titulo))
    elements.append(Paragraph(f"CONTRIBUYENTE: {cliente.nombre}", estilo_sub))
    elements.append(Paragraph(f"NRC: {cliente.nrc}  |  NIT: {cliente.nit}", estilo_sub))
    elements.append(Paragraph(f"PERÍODO: {periodo}  |  MONEDA: USD", estilo_sub))
    elements.append(Spacer(1, 10))

    # Tabla
    # Ajusté ligeramente los anchos para asegurar que quepan en Carta (Total aprox 750 pts)
    col_widths = [30, 55, 160, 50, 140, 50, 50, 50, 45, 55, 45, 45]
    headers = ['No.', 'FECHA', 'Nº COMPROBANTE / DTE', 'NRC', 'PROVEEDOR', 'EXENTAS', 'GRAV. LOC', 'GRAV. IMP', 'IVA', 'TOTAL', 'RET 1%', 'RET 13%']
    data = [headers]

    t_exenta = 0; t_grav_loc = 0; t_grav_imp = 0; t_iva = 0; t_total = 0; t_ret1 = 0; t_ret13 = 0
    correlativo = 1
    
    estilo_celda = ParagraphStyle(name='Celda', fontSize=7, leading=8, alignment=TA_LEFT)
    estilo_celda_num = ParagraphStyle(name='CeldaNum', fontSize=7, leading=8, alignment=TA_RIGHT)

    for c in compras:
        es_importacion = c.tipo_documento == '12'
        exenta = 0.00
        grav_loc = float(c.monto_gravado) if not es_importacion else 0.00
        grav_imp = float(c.monto_gravado) if es_importacion else 0.00
        iva = float(c.monto_iva)
        total = float(c.monto_total)
        ret1 = 0.00 
        ret13 = 0.00

        t_exenta += exenta; t_grav_loc += grav_loc; t_grav_imp += grav_imp
        t_iva += iva; t_total += total; t_ret1 += ret1; t_ret13 += ret13

        fila = [
            str(correlativo),
            c.fecha_emision.strftime("%d/%m/%Y"),
            Paragraph(c.codigo_generacion or "", estilo_celda),
            c.nrc_proveedor,
            Paragraph(c.nombre_proveedor, estilo_celda),
            Paragraph(f"{exenta:,.2f}", estilo_celda_num),
            Paragraph(f"{grav_loc:,.2f}", estilo_celda_num),
            Paragraph(f"{grav_imp:,.2f}", estilo_celda_num),
            Paragraph(f"{iva:,.2f}", estilo_celda_num),
            Paragraph(f"{total:,.2f}", estilo_celda_num),
            Paragraph(f"{ret1:,.2f}", estilo_celda_num),
            Paragraph(f"{ret13:,.2f}", estilo_celda_num),
        ]
        data.append(fila)
        correlativo += 1

    data.append(['', '', 'TOTALES:', '', '', f"${t_exenta:,.2f}", f"${t_grav_loc:,.2f}", f"${t_grav_imp:,.2f}", f"${t_iva:,.2f}", f"${t_total:,.2f}", f"${t_ret1:,.2f}", f"${t_ret13:,.2f}"])

    tabla = Table(data, colWidths=col_widths, repeatRows=1)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.whitesmoke),
    ]))
    elements.append(tabla)

    elements.append(Spacer(1, 50))
    data_firmas = [['_________________________', '_________________________'], ['F. CONTADOR', 'F. REPRESENTANTE LEGAL']]
    tabla_firmas = Table(data_firmas, colWidths=[250, 250]) # Ajustado para Carta
    tabla_firmas.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    elements.append(tabla_firmas)

    doc.build(elements)
    return response
# 11. PDF VENTAS CONSUMIDOR FINAL (CARTA) -

@api_view(['GET'])
def generar_pdf_ventas_cf(request):
    cliente_id = request.query_params.get('nrc')
    periodo = request.query_params.get('periodo')
    
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib import colors
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="LIBRO_VENTAS_CF_{periodo}.pdf"'

    try:
        cliente = Cliente.objects.get(nrc=cliente_id)
        ventas = Venta.objects.filter(cliente=cliente, periodo_aplicado=periodo, tipo_venta='CF').order_by('fecha_emision', 'numero_control')
    except Cliente.DoesNotExist:
        return HttpResponse("Cliente no encontrado", status=404)

    doc = SimpleDocTemplate(response, pagesize=landscape(letter), rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=20)
    elements = []
    styles = getSampleStyleSheet()

    estilo_titulo = ParagraphStyle(name='Titulo', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=12, spaceAfter=2)
    estilo_sub = ParagraphStyle(name='Sub', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10)

    elements.append(Paragraph("LIBRO DE VENTAS A CONSUMIDOR FINAL", estilo_titulo))
    elements.append(Paragraph(f"{cliente.nombre}", estilo_sub))
    elements.append(Paragraph(f"Periodo del: {periodo} | DUI:{cliente.dui} NRC: {cliente.nrc}", estilo_sub))
    elements.append(Paragraph("(Cifras Expresadas en Dolares de los Estados Unidos de America)", estilo_sub))
    elements.append(Spacer(1, 15))

    resumen_diario = {}
    
    for v in ventas:
        fecha = v.fecha_emision.strftime("%d/%m/%Y")
        
        # --- CORRECCIÓN CRÍTICA "NONE" ---
        if v.clase_documento == '4': # DTE
            # Buscamos el Código Generación. Si está vacío, usamos numero_documento. Si ambos fallan, string vacío.
            # IMPORTANTE: Convertimos a string (str) para evitar que salga "None" literal.
            raw_val = v.codigo_generacion or v.numero_documento or ""
            valor_visual = str(raw_val)
        else:
            # Físico
            raw_val = v.numero_control_desde or v.numero_documento or ""
            valor_visual = str(raw_val)

        if fecha not in resumen_diario:
            resumen_diario[fecha] = {
                "caja": "GEN", # Puedes mapear esto a un campo de caja si lo tuvieras
                "del_num": valor_visual,
                "al_num": valor_visual,
                "exentas": 0.0, "no_sujetas": 0.0, "gravadas": 0.0, "total": 0.0
            }
        
        # Actualizamos "Al"
        resumen_diario[fecha]["al_num"] = valor_visual
        
        total_venta = float(v.venta_gravada) + float(v.debito_fiscal)
        
        if v.clasificacion_venta == "2": resumen_diario[fecha]["exentas"] += total_venta
        elif v.clasificacion_venta == "3": resumen_diario[fecha]["no_sujetas"] += total_venta
        else: resumen_diario[fecha]["gravadas"] += total_venta
        
        resumen_diario[fecha]["total"] += total_venta

    # Tabla
    headers_1 = ['Día', 'Nº de CAJA', 'Correlativo', '', 'Ventas', '', '', 'Export.', 'Retención', 'Venta']
    headers_2 = ['', '', 'Del Nº', 'Al Nº', 'No Sujetas', 'Exentas', 'Gravadas', '', 'IVA 1%', 'Total']
    data = [headers_1, headers_2]

    t_no_suj = 0; t_exenta = 0; t_grav = 0; t_total = 0
    
    # Estilo UUID (letra muy pequeña para que quepa el código largo)
    estilo_uuid = ParagraphStyle(name='UUID', fontSize=5, alignment=TA_CENTER, leading=6)
    estilo_celda = ParagraphStyle(name='Celda', fontSize=8, alignment=TA_CENTER)

    for fecha, info in resumen_diario.items():
        t_no_suj += info["no_sujetas"]; t_exenta += info["exentas"]; t_grav += info["gravadas"]; t_total += info["total"]

        # Determinamos si usamos estilo pequeño (UUID largo) o normal
        estilo_uso = estilo_uuid if len(info["del_num"]) > 15 else estilo_celda

        row = [
            fecha,
            info["caja"],
            Paragraph(info["del_num"], estilo_uso), # ¡Ahora sí mostrará el código!
            Paragraph(info["al_num"], estilo_uso),
            f"${info['no_sujetas']:,.2f}" if info['no_sujetas'] > 0 else "",
            f"${info['exentas']:,.2f}" if info['exentas'] > 0 else "",
            f"${info['gravadas']:,.2f}",
            "", "",
            f"${info['total']:,.2f}"
        ]
        data.append(row)

    data.append(['', '', 'TOTALES:', '', f"${t_no_suj:,.2f}", f"${t_exenta:,.2f}", f"${t_grav:,.2f}", '', '', f"${t_total:,.2f}"])

    col_widths = [50, 40, 130, 130, 60, 60, 70, 50, 60, 70] # Columnas UUID más anchas
    
    tabla = Table(data, colWidths=col_widths, repeatRows=2)
    tabla.setStyle(TableStyle([
        ('SPAN', (0,0), (0,1)), ('SPAN', (1,0), (1,1)), ('SPAN', (2,0), (3,0)), ('SPAN', (4,0), (6,0)), ('SPAN', (7,0), (7,1)), ('SPAN', (8,0), (8,1)), ('SPAN', (9,0), (9,1)),
        ('BACKGROUND', (0, 0), (-1, 1), colors.lightgrey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.whitesmoke),
        ('ALIGN', (4, 2), (-1, -1), 'RIGHT'),
    ]))
    elements.append(tabla)

    elements.append(Spacer(1, 40))
    data_firmas = [['_________________________', '_________________________'], ['F. CONTADOR', 'F. REPRESENTANTE LEGAL']]
    tabla_firmas = Table(data_firmas, colWidths=[250, 250])
    tabla_firmas.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    elements.append(tabla_firmas)

    doc.build(elements)
    return response

    # 12. PDF VENTAS CONTRIBUYENTES (CCF) - ¡NUEVA!
@api_view(['GET'])
def generar_pdf_ventas_ccf(request):
    cliente_id = request.query_params.get('nrc')
    periodo = request.query_params.get('periodo')
    
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    from reportlab.lib import colors
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="LIBRO_VENTAS_CCF_{periodo}.pdf"'

    try:
        cliente = Cliente.objects.get(nrc=cliente_id)
        # Solo Ventas CCF
        ventas = Venta.objects.filter(cliente=cliente, periodo_aplicado=periodo, tipo_venta='CCF').order_by('fecha_emision', 'numero_documento')
    except Cliente.DoesNotExist:
        return HttpResponse("Cliente no encontrado", status=404)

    doc = SimpleDocTemplate(response, pagesize=landscape(letter), rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=20)
    elements = []
    styles = getSampleStyleSheet()

    # --- ENCABEZADO ---
    estilo_titulo = ParagraphStyle(name='Titulo', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=12, spaceAfter=2)
    estilo_sub = ParagraphStyle(name='Sub', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10)

    # Articulo a la derecha (como en tu ejemplo)
    estilo_derecha = ParagraphStyle(name='Der', parent=styles['Normal'], alignment=TA_RIGHT, fontSize=8)
    elements.append(Paragraph("Art. 85 R.A.C.T.", estilo_derecha))
    
    elements.append(Paragraph("LIBRO DE VENTAS A CONTRIBUYENTES", estilo_titulo))
    elements.append(Paragraph(f"{cliente.nombre}", estilo_sub))
    elements.append(Paragraph(f"Periodo del: {periodo} | DUI:{cliente.dui} NRC: {cliente.nrc}", estilo_sub))
    elements.append(Paragraph("(Cifras Expresadas en Dolares de los Estados Unidos de America)", estilo_sub))
    elements.append(Spacer(1, 15))

    # --- TABLA DE DATOS ---
    # Encabezados (Fila 1 y 2 para agrupar títulos)
    headers_1 = ['No', 'Día', 'Nº de', 'Nombre del', 'Nº de', 'Ventas Internas', '', '', 'Débito', 'IVA 1%', 'Venta']
    headers_2 = ['Corr.', '', 'Comprob.', 'Cliente', 'Reg.', 'Exentas', 'Gravadas', '', 'Fiscal', 'Retenido', 'Total']
    
    # Nota: Simplifiqué algunas columnas vacías (Exportaciones, Terceros) para que quepa mejor y se vea limpio, 
    # pero si las necesitas obligatoriamente las agregamos.

    data = [headers_1, headers_2]

    # Variables de Totales
    t_exenta = 0; t_gravada = 0; t_debito = 0; t_ret1 = 0; t_total = 0
    correlativo = 1

    estilo_celda = ParagraphStyle(name='Celda', fontSize=7, leading=8, alignment=TA_LEFT)
    estilo_num = ParagraphStyle(name='Num', fontSize=7, leading=8, alignment=TA_RIGHT)

    for v in ventas:
        # Cálculos
        gravada = float(v.venta_gravada)
        debito = float(v.debito_fiscal)
        exenta = 0.00 # (Si tuvieras ventas exentas CCF, iría aquí)
        if v.clasificacion_venta == "2": # Si marcaste exenta
             exenta = gravada
             gravada = 0.00
             debito = 0.00
        
        # OJO: El total suele ser Gravado + IVA
        total = gravada + debito + exenta
        ret1 = float(v.iva_retenido_1) # Retención que nos hicieron (si aplica)

        # Sumar Totales Generales
        t_exenta += exenta; t_gravada += gravada; t_debito += debito
        t_ret1 += ret1; t_total += total

        # Formato de Fecha (Solo día o dd/mm)
        dia = v.fecha_emision.strftime("%d/%m") 

        row = [
            str(correlativo),
            dia,
            v.numero_documento or v.codigo_generacion, # Prioridad al corto
            Paragraph(v.nombre_receptor[:35], estilo_celda), # Recortar nombre largo
            v.nrc_receptor,
            f"${exenta:,.2f}" if exenta > 0 else "",
            f"${gravada:,.2f}",
            "", # Espacio extra visual
            f"${debito:,.2f}",
            f"${ret1:,.2f}" if ret1 > 0 else "",
            f"${total:,.2f}"
        ]
        data.append(row)
        correlativo += 1

    # Fila de Totales
    data.append([
        '', '', '', 'TOTALES:', '',
        f"${t_exenta:,.2f}", f"${t_gravada:,.2f}", '', f"${t_debito:,.2f}", 
        f"${t_ret1:,.2f}", f"${t_total:,.2f}"
    ])

    # Anchos de Columna (Total ~750 puntos)
    col_widths = [25, 35, 70, 180, 50, 55, 55, 10, 55, 55, 60]
    
    tabla = Table(data, colWidths=col_widths, repeatRows=2)
    tabla.setStyle(TableStyle([
        ('SPAN', (0,0), (0,1)), ('SPAN', (1,0), (1,1)), ('SPAN', (2,0), (2,1)), ('SPAN', (3,0), (3,1)), 
        ('SPAN', (4,0), (4,1)), ('SPAN', (5,0), (7,0)), # Unir Ventas Internas
        ('SPAN', (8,0), (8,1)), ('SPAN', (9,0), (9,1)), ('SPAN', (10,0), (10,1)),
        
        ('BACKGROUND', (0, 0), (-1, 1), colors.lightgrey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.whitesmoke),
        ('ALIGN', (5, 2), (-1, -1), 'RIGHT'), # Números a la derecha
    ]))
    elements.append(tabla)

    elements.append(Spacer(1, 50))
    data_firmas = [['_________________________', '_________________________'], ['F. CONTADOR', 'F. REPRESENTANTE LEGAL']]
    tabla_firmas = Table(data_firmas, colWidths=[250, 250])
    tabla_firmas.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    elements.append(tabla_firmas)

    doc.build(elements)
    return response
# --- REPORTES CSV (INCLUYENDO EL NUEVO DE PERCEPCIONES) ---

@api_view(['GET'])
def generar_csv_163(request): # PERCEPCIÓN (ANEXO 10)
    cliente_id = request.query_params.get('nrc')
    periodo = request.query_params.get('periodo')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="ANEXO_163_{periodo}.csv"'
    writer = csv.writer(response, delimiter=';')

    # Buscamos compras que tengan percepción > 0
    compras_per = Compra.objects.filter(cliente__nrc=cliente_id, periodo_aplicado=periodo, monto_percepcion__gt=0)

    for c in compras_per:
        fecha_fmt = c.fecha_emision.strftime("%d/%m/%Y")
        # Mapeo según estructura Anexo 10 (NIT, Fecha, Doc, Serie, Monto Sujeto, Percepción, Anexo)
        nit_limpio = "" # Tendríamos que guardar el NIT del proveedor en la compra si no está
        # Para el ejemplo, asumimos que lo tenemos o lo dejamos vacío para llenar
        
        fila = [
            nit_limpio,
            fecha_fmt,
            c.codigo_generacion, # Doc
            "SERIE", # Serie
            format(c.monto_gravado + c.monto_iva, '.2f'), # Monto Sujeto (Total)
            format(c.monto_percepcion, '.2f'), # Percepción
            "0.00",
            "10" # Tipo Anexo 10
        ]
        writer.writerow(fila)
    return response