import json
import uuid # Librería para generar códigos únicos
from datetime import datetime

def generar_dte_dinamico():
    # 1. Generamos los códigos únicos para ESTA transacción
    # Genera un UUID v4 (Estándar internacional) y lo pone en mayúsculas
    codigo_unico = str(uuid.uuid4()).upper() 
    
    # Generamos fecha y hora actuales
    ahora = datetime.now()
    fecha_hoy = ahora.strftime("%Y-%m-%d")
    hora_hoy = ahora.strftime("%H:%M:%S")

    # 2. Construimos el DTE
    dte = {
        "identificacion": {
            "version": 1,
            "ambiente": "00",        # 00 = Pruebas
            "tipoDte": "01",         # 01 = Factura
            # IMPORTANTE: Aquí simulamos un correlativo. 
            # En tu sistema real, esto debe venir de tu base de datos (+1 al anterior)
            "numeroControl": "DTE-01-00000001", 
            "codigoGeneracion": codigo_unico, # ¡DINÁMICO!
            "tipoModelo": 1,
            "tipoOperacion": 1,
            "fecEmi": fecha_hoy,     # ¡DINÁMICO!
            "horEmi": hora_hoy,      # ¡DINÁMICO!
            "tipoMoneda": "USD"
        },
        "documentoRelacionado": None,
        "emisor": {
            "nit": "12092310921022", # Tu NIT correcto
            "nrc": "2984414",        # Tu NRC correcto
            "nombre": "FRANCISCO JOSE SALAMANCA GONZALEZ", # Tu nombre real según el portal
            "codActividad": "12345",
            "descActividad": "VENTA DE HARDWARE",
            "direccion": {
                "departamento": "06",
                "municipio": "14",
                "complemento": "Calle Principal #123"
            },
            "telefono": "22222222",
            "correo": "tucorreo@email.com"
        },
        "receptor": {
            "tipoDocumento": "36",
            "numDocumento": "06142803901121",
            "nombre": "CLIENTE DE PRUEBA",
            "correo": "cliente@prueba.com"
        },
        "otrosDocumentos": None,
        "ventaTercero": None,
        "cuerpoDocumento": [
            {
                "numItem": 1,
                "tipoItem": 1,
                "cantidad": 1.0,
                "codigo": "PROD001",
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
            "totalLetras": "DIEZ 00/100 USD",
            "condicionOperacion": 1
        },
        "extension": None,
        "apendice": None
    }

    # Devolvemos el diccionario (objeto) para usarlo después
    return dte

# Prueba rápida
if __name__ == "__main__":
    factura = generar_dte_dinamico()
    print("✅ Factura generada con UUID:", factura["identificacion"]["codigoGeneracion"])
    # print(json.dumps(factura, indent=4)) # Descomenta para ver todo el JSON