import requests
import json
import uuid
from datetime import datetime

# --- CONFIGURACIÓN ---
URL_FIRMADOR = "http://localhost:8113/firmardocumento/"  # Tu Docker Local
NIT_EMISOR = "12092310921022"                            # Tu NIT (Sin guiones)
CLAVE_DEL_CERTIFICADO = "Salamanca92"      # ¡IMPORTANTE!

def generar_dte_prueba():
    # Generamos un DTE simple para probar
    dte = {
        "identificacion": {
            "version": 1,
            "ambiente": "00",
            "tipoDte": "01",
            "numeroControl": "DTE-01-00000001",
            "codigoGeneracion": str(uuid.uuid4()).upper(),
            "tipoModelo": 1,
            "tipoOperacion": 1,
            "fecEmi": datetime.now().strftime("%Y-%m-%d"),
            "horEmi": datetime.now().strftime("%H:%M:%S"),
            "tipoMoneda": "USD"
        },
        "documentoRelacionado": None,
        "emisor": {
            "nit": NIT_EMISOR,
            "nrc": "2984414",
            "nombre": "FRANCISCO JOSE SALAMANCA GONZALEZ",
            "codActividad": "12345",
            "descActividad": "VENTA DE HARDWARE",
            "direccion": {
                "departamento": "06",
                "municipio": "14",
                "complemento": "Calle Principal"
            },
            "telefono": "22222222",
            "correo": "tucorreo@email.com"
        },
        "receptor": {
            "tipoDocumento": "36",
            "numDocumento": "06142803901121",
            "nombre": "CLIENTE PRUEBA",
            "correo": "cliente@test.com"
        },
        "otrosDocumentos": None,
        "ventaTercero": None,
        "cuerpoDocumento": [
            {
                "numItem": 1,
                "tipoItem": 1,
                "cantidad": 1.0,
                "codigo": "123",
                "descripcion": "Martillo",
                "precioUni": 10.0,
                "montoDescu": 0.0,
                "ventaNoSuj": 0.0,
                "ventaExenta": 0.0,
                "ventaGravada": 10.0,
                "tributos": []
            }
        ],
        "resumen": {
            "totalNoSuj": 0.0,
            "totalExenta": 0.0,
            "totalGravada": 10.0,
            "subTotal": 10.0,
            "montoTotalOperacion": 10.0,
            "totalNoGravado": 0.0,
            "totalPagar": 10.0,
            "totalLetras": "DIEZ USD",
            "condicionOperacion": 1
        },
        "extension": None,
        "apendice": None
    }
    return dte

def firmar_documento():
    print("1. Generando JSON de Factura...")
    json_factura = generar_dte_prueba()
    
    # Preparamos el paquete para el Firmador (Docker)
    payload = {
        "nit": NIT_EMISOR,
        "activo": True,
        "passwordPri": CLAVE_DEL_CERTIFICADO, # El firmador pide esto para desbloquear la llave
        "dteJson": json_factura
    }
    
    headers = {'Content-Type': 'application/json'}

    print("2. Enviando a Docker para firmar (localhost:8113)...")
    
    try:
        respuesta = requests.post(URL_FIRMADOR, json=payload, headers=headers)
        
        if respuesta.status_code == 200:
            datos = respuesta.json()
            if datos.get("status") == "OK":
                firma = datos.get("body")
                print("\n✅ ¡ÉXITO! DOCUMENTO FIRMADO.")
                print(f"Firma (JWS): {firma[:50]}...") # Mostramos el inicio
                return firma
            else:
                print("\n❌ Error del Firmador:", datos)
        else:
            print(f"\n❌ Error de Conexión: {respuesta.status_code}")
            print(respuesta.text)

    except Exception as e:
        print(f"\n❌ Error crítico: {e}")
        print("Asegúrate de que Docker esté corriendo.")

# Ejecutar
firmar_documento()