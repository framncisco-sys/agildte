"""
Extrae el documento completo que se enviaría a MH (con firma JWS).
Lo guarda en un JSON sin enviarlo, para que puedas adjuntarlo al correo de soporte a Hacienda.
"""
import os
import sys
import json
import django
from datetime import datetime

# Configurar encoding para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_contable.settings')
django.setup()

from api.models import Venta, Empresa
from api.services.facturacion_service import FacturacionService
from api.dte_generator import DTEGenerator


def extraer_documento_mh(venta_id=None):
    """
    Genera el documento firmado que se enviaría a MH y lo guarda en un archivo JSON.
    No envía nada a MH.
    """
    print("EXTRAYENDO DOCUMENTO PARA ENVIO A MH (sin enviar)...")
    
    # Obtener venta
    if venta_id:
        venta = Venta.objects.filter(id=venta_id).first()
    else:
        venta = Venta.objects.last()
    
    if not venta:
        print("ERROR: No hay ventas en la base de datos.")
        return None
    
    print(f"Venta ID: {venta.id} | Cliente: {venta.cliente.nombre}")
    
    try:
        servicio = FacturacionService(venta.empresa)
        
        # 1. Generar JSON DTE
        print("Generando JSON DTE...")
        gen = DTEGenerator(venta)
        json_dte = gen.generar_json(ambiente=servicio.codigo_ambiente_mh)
        
        codigo_generacion = (venta.codigo_generacion or json_dte['identificacion']['codigoGeneracion'] or '').upper()
        tipo_dte = '01' if venta.tipo_venta == 'CF' else '03'
        
        # 2. Firmar documento
        print("Firmando documento...")
        dte_firmado = servicio.firmar_dte(json_dte)
        
        if not dte_firmado:
            print("ERROR: No se pudo firmar el documento.")
            return None
        
        # 3. Construir payload exacto que se enviaria a MH (Schema 2025 V3)
        version_envio = 3  # Obligatorio V3 para MH 2025
        payload_mh = {
            "ambiente": servicio.codigo_ambiente_mh,
            "idEnvio": 1,
            "version": version_envio,
            "tipoDte": tipo_dte,
            "documento": dte_firmado,
            "codigoGeneracion": codigo_generacion
        }
        
        # 4. Guardar en archivo
        nombre_archivo = f"DOCUMENTO_MH_V{venta.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(nombre_archivo, 'w', encoding='utf-8') as f:
            json.dump(payload_mh, f, indent=4, ensure_ascii=False)
        
        print("\n" + "="*60)
        print("OK - Documento extraido correctamente")
        print("="*60)
        print(f"Archivo generado: {nombre_archivo}")
        print("Este es el documento completo (con firma) que se envia a MH.")
        print("Puedes adjuntarlo al correo de soporte a Hacienda.")
        print("="*60)
        
        return nombre_archivo
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # Opcional: pasar ID de venta como argumento
    venta_id = int(sys.argv[1]) if len(sys.argv) > 1 else None
    extraer_documento_mh(venta_id)
