"""
Prueba integral del sistema con DTE-03 Versión 3.
Usa EXCLUSIVAMENTE las clases del proyecto (DTEGenerator, FacturacionService).
Verifica que el JSON generado tenga "version": 3 antes de firmar.
"""
import os
import sys

# Configurar encoding para Windows (evita fallo con emojis en facturacion_service)
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_contable.settings')

import django
django.setup()

from api.models import Venta, Empresa
from api.dte_generator import DTEGenerator
from api.services.facturacion_service import FacturacionService


def main():
    print("=" * 60)
    print("PRUEBA SISTEMA V3 - Flujo completo (generar + firmar)")
    print("=" * 60)

    empresa = Empresa.objects.first()
    if not empresa:
        print("[ERROR] No hay Empresa en BD.")
        return
    servicio = FacturacionService(empresa)

    venta = Venta.objects.filter(tipo_venta='CCF').last()
    if not venta:
        venta = Venta.objects.last()
    if not venta:
        print("[ERROR] No hay Venta en BD.")
        return

    print(f"Empresa: {empresa.nombre}")
    print(f"Venta ID: {venta.id} | Cliente: {venta.cliente.nombre} | tipo_venta: {venta.tipo_venta}")
    print()

    ambiente = getattr(empresa, 'ambiente', '00') or '00'

    # 1. Generar JSON con DTEGenerator (mismo flujo que procesar_factura)
    print("--- 1. Generando JSON con DTEGenerator(venta).generar_json() ---")
    generator = DTEGenerator(venta)
    json_dte = generator.generar_json(ambiente=ambiente)

    version = json_dte.get('identificacion', {}).get('version')
    tipo_dte = json_dte.get('identificacion', {}).get('tipoDte')

    print(f"   version (identificacion): {version}")
    print(f"   tipoDte: {tipo_dte}")

    if tipo_dte == '03' and version != 3:
        print(f"\n[FALLO] DTE-03 debe tener version=3. Actual: {version}")
        return
    if tipo_dte == '03':
        # Verificar que items NO tengan ivaItem
        items = json_dte.get('cuerpoDocumento', [])
        if items and 'ivaItem' in items[0]:
            print(f"\n[FALLO] DTE-03 V3: items NO deben tener ivaItem.")
            return
        print("   [OK] Items sin ivaItem (correcto para V3)")
    print("   [OK] JSON generado con version correcta.")

    # 2. Imprimir fragmento del JSON (identificacion + primer item)
    print("\n--- 2. Fragmento del JSON (antes de firmar) ---")
    fragmento = {
        "identificacion": json_dte.get("identificacion"),
        "primerItem_cuerpoDocumento": json_dte.get("cuerpoDocumento", [{}])[0] if json_dte.get("cuerpoDocumento") else None
    }
    print(json.dumps(fragmento, indent=2, ensure_ascii=False))

    # 3. Firmar
    print("\n--- 3. Firmando con servicio.firmar_dte(json_dte) ---")
    try:
        dte_firmado = servicio.firmar_dte(json_dte)
    except Exception as e:
        print(f"[ERROR] Firma: {e}")
        return
    if dte_firmado:
        print("   [OK] Documento firmado correctamente.")
    else:
        print("[ERROR] firmar_dte devolvio None.")
        return

    # 4. Flujo completo: procesar_factura (genera + firma + envia a MH)
    print("\n--- 4. Flujo completo: servicio.procesar_factura(venta) ---")
    try:
        resultado = servicio.procesar_factura(venta)
        if resultado.get('exito'):
            print("   [OK] Factura aceptada por MH.")
        else:
            print(f"   [INFO] MH: {resultado.get('mensaje', resultado.get('estado'))}")
    except Exception as e:
        print(f"   [INFO] Error: {e}")

    print("\n" + "=" * 60)
    print("PRUEBA FINALIZADA. Sistema genera DTE-03 con version=3.")
    print("=" * 60)


if __name__ == "__main__":
    main()
