import requests
import json
import uuid
from datetime import datetime

# =============================================================================
# ⚙️ CONFIGURACIÓN DE TU EMPRESA (LLENAR ESTO CON CUIDADO)
# =============================================================================

# TUS CREDENCIALES
NIT_EMISOR      = "12092310921022"                  # Tu NIT sin guiones
NRC_EMISOR      = "2984414"                         # Tu NRC
NOMBRE_EMISOR   = "FRANCISCO JOSE SALAMANCA GONZALEZ"
CLAVE_API_MH    = "2Caballoblanco.verde"            # La que creaste en el portal
CLAVE_CERT_CRT  = "Salamanca92"        # La contraseña del archivo .crt

# DATOS DEL CLIENTE DE PRUEBA
NIT_CLIENTE     = "06142803901121"
NOMBRE_CLIENTE  = "CLIENTE DE PRUEBA"
CORREO_CLIENTE  = "cliente@prueba.com"

# URLS DEL SISTEMA
URL_MH_AUTH     = "https://apitest.dtes.mh.gob.sv/seguridad/auth"         # [cite: 562]
URL_MH_RECEPCION= "https://apitest.dtes.mh.gob.sv/fesv/recepciondte"      # [cite: 616]
URL_FIRMADOR    = "http://localhost:8113/firmardocumento/"                # Tu Docker

# =============================================================================
# 1. FUNCIÓN: AUTENTICARSE CON HACIENDA (Obtener Token)
# =============================================================================
def obtener_token():
    payload = { "user": NIT_EMISOR, "pwd": CLAVE_API_MH }
    headers = { "Content-Type": "application/x-www-form-urlencoded", "User-Agent": "Mozilla/5.0" }
    
    try:
        resp = requests.post(URL_MH_AUTH, data=payload, headers=headers)
        if resp.status_code == 200:
            return resp.json().get("body", {}).get("token")
        else:
            print("❌ Error Auth:", resp.text)
            return None
    except Exception as e:
        print("❌ Error Conexión Auth:", e)
        return None

# =============================================================================
# 2. FUNCIÓN: CREAR EL JSON DE LA FACTURA (VERSIÓN CORREGIDA Y COMPLETA)
# =============================================================================
def crear_json_dte(codigo_unico):
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    hora_hoy  = datetime.now().strftime("%H:%M:%S")
    
    # DATOS DE CONFIGURACIÓN
    COD_ESTABLECIMIENTO = "M001"
    COD_PUNTO_VENTA     = "P001"
    
    # Correlativo (En producción esto debe venir de tu base de datos)
    correlativo = "000000000000001" 
    numero_control = f"DTE-01-{COD_ESTABLECIMIENTO}{COD_PUNTO_VENTA}-{correlativo}"

    dte = {
        "identificacion": {
            "version": 1,
            "ambiente": "00",       # Pruebas
            "tipoDte": "01",        # Factura
            "numeroControl": numero_control,
            "codigoGeneracion": codigo_unico,
            "tipoModelo": 1,
            "tipoOperacion": 1,
            "tipoContingencia": None,
            "motivoContin": None,
            "fecEmi": fecha_hoy,
            "horEmi": hora_hoy,
            "tipoMoneda": "USD"
        },
        "documentoRelacionado": None,
        "emisor": {
            "nit": NIT_EMISOR,
            "nrc": NRC_EMISOR,
            "nombre": NOMBRE_EMISOR,
            "codActividad": "47520", 
            "descActividad": "VENTA DE ARTICULOS DE FERRETERIA",
            "nombreComercial": "TU FERRETERIA",
            "tipoEstablecimiento": "02", # 02 = Casa Matriz (Cambié a 02 por si acaso)
            "direccion": {
                "departamento": "06",
                "municipio": "14",
                "complemento": "COLONIA ESCALON, CALLE PRINCIPAL #123"
            },
            "telefono": "22222222",
            "correo": "tu@email.com",
            "codEstableMH": None,
            "codEstable": COD_ESTABLECIMIENTO,
            "codPuntoVentaMH": None, 
            "codPuntoVenta": COD_PUNTO_VENTA
        },
        "receptor": {
            "tipoDocumento": "36",
            "numDocumento": NIT_CLIENTE,
            "nombre": NOMBRE_CLIENTE,
            "correo": CORREO_CLIENTE,
            "codActividad": None,
            "nrc": None,
            "descActividad": None,
            "direccion": {
                "departamento": "06",
                "municipio": "14",
                "complemento": "San Salvador"
            },
            "telefono": "77777777"
        },
        "otrosDocumentos": None,
        "ventaTercero": None,
        "cuerpoDocumento": [
            {
                "numItem": 1,
                "tipoItem": 1,
                "numeroDocumento": None,
                "cantidad": 1.0,
                "codigo": "ITEM01",
                "codTributo": None,
                "uniMedida": 59,
                "descripcion": "Martillo Premium",
                "precioUni": 10.00,
                "montoDescu": 0.00,
                "ventaNoSuj": 0.00,
                "ventaExenta": 0.00,
                "ventaGravada": 10.00,
                "tributos": None,        # CORREGIDO: Debe ser null para facturas normales
                "psv": 0.00,
                "noGravado": 0.00,
                "ivaItem": 1.15
            }
        ],
        "resumen": {
            "totalNoSuj": 0.00,
            "totalExenta": 0.00,
            "totalGravada": 10.00,
            "subTotalVentas": 10.00,
            "descuNoSuj": 0.00,
            "descuExenta": 0.00,
            "descuGravada": 0.00,
            "porcentajeDescuento": 0.00,
            "totalDescu": 0.00,
            "tributos": None,            # CORREGIDO: Debe ser null si no hay impuestos especiales
            "subTotal": 10.00,
            "ivaRete1": 0.00,
            "reteRenta": 0.00,
            "montoTotalOperacion": 10.00,
            "totalNoGravado": 0.00,
            "totalPagar": 10.00,
            "totalLetras": "DIEZ 00/100 USD",
            "totalIva": 1.15,
            "saldoFavor": 0.00,
            "condicionOperacion": 1,
            "pagos": [
                {
                    "codigo": "01",
                    "montoPago": 10.00,
                    "referencia": None,
                    "plazo": None,
                    "periodo": None
                }
            ],
            "numPagoElectronico": None
        },
        "extension": None,
        "apendice": None
    }
    return dte

# =============================================================================
# 3. FUNCIÓN: FIRMAR EL DOCUMENTO (Docker)
# =============================================================================
def firmar_dte(json_dte):
    payload = {
        "nit": NIT_EMISOR,
        "activo": True,
        "passwordPri": CLAVE_CERT_CRT,
        "dteJson": json_dte
    }
    headers = {'Content-Type': 'application/json'}
    
    try:
        resp = requests.post(URL_FIRMADOR, json=payload, headers=headers)
        if resp.status_code == 200:
            datos = resp.json()
            if datos.get("status") == "OK":
                return datos.get("body") # Retorna el JWS Firmado
            else:
                print("❌ Error Firmador:", datos)
                return None
        else:
            print("❌ Error Conexión Firmador:", resp.status_code)
            return None
    except Exception as e:
        print("❌ Error Docker:", e)
        return None

# =============================================================================
# 4. FUNCIÓN PRINCIPAL: ORQUESTAR TODO EL PROCESO
# =============================================================================
def procesar_factura():
    print("🚀 INICIANDO PROCESO DE FACTURACIÓN ELECTRÓNICA...")
    
    # PASO A: Obtener Token
    print("\n1. Obteniendo Token de Hacienda...")
    token = obtener_token()
    if not token: return
    print("   ✅ Token recibido.")

    # PASO B: Generar JSON
    print("\n2. Creando Factura...")
    uuid_dte = str(uuid.uuid4()).upper()
    json_dte = crear_json_dte(uuid_dte)
    print(f"   ✅ Factura generada (UUID: {uuid_dte})")

    # PASO C: Firmar
    print("\n3. Firmando documento...")
    dte_firmado = firmar_dte(json_dte)
    if not dte_firmado: return
    print("   ✅ Documento firmado correctamente (JWS generado).")

    # PASO D: Enviar a Hacienda
    print("\n4. 📤 ENVIANDO A MINISTERIO DE HACIENDA...")
    
    # [cite_start]Estructura de envío según Manual [cite: 619]
    envio_mh = {
        "ambiente": "00",
        "idEnvio": 1,
        "version": 1,           # Versión del esquema de envío
        "tipoDte": "01",        # Factura
        "documento": dte_firmado, # El JWS que nos dio Docker
        "codigoGeneracion": uuid_dte
    }
    
    headers_mh = {
        "Authorization": token,  # Aquí va el token Bearer
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    try:
        resp = requests.post(URL_MH_RECEPCION, json=envio_mh, headers=headers_mh)
        
        print(f"   📡 Respuesta Servidor: {resp.status_code}")
        
        if resp.status_code == 200 or resp.status_code == 201:
            datos = resp.json()
            estado = datos.get("estado")
            
            if estado == "PROCESADO":
                sello = datos.get("selloRecibido")
                print("\n🎉🎉🎉 ¡ÉXITO TOTAL! FACTURA ACEPTADA 🎉🎉🎉")
                print(f"📜 SELLO DE RECEPCIÓN: {sello}")
                print(f"🔗 Código Generación: {uuid_dte}")
                print("\n(Guarda este sello, debe ir impreso en el PDF)")
            else:
                print("\n⚠️ RECIBIDO PERO RECHAZADO:")
                print("Mensaje:", datos.get("descripcionMsg"))
                print("Observaciones:", datos.get("observaciones"))
        else:
            print("\n❌ Error en el envío:")
            print(resp.text)
            
    except Exception as e:
        print("❌ Error crítico enviando a MH:", e)

# EJECUTAR TODO
if __name__ == "__main__":
    procesar_factura()