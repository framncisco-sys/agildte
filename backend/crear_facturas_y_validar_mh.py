"""
Crea facturas de prueba (reset de ventas anteriores) y valida emisión con MH.

Usa ventas existentes, las resetea a Borrador y las re-emite para validar
el esquema corregido contra MH.
"""
import os
import sys
from datetime import date

# Configurar encoding para Windows
if sys.platform == 'win32':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except Exception:
        pass

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_contable.settings')
import django
django.setup()

from api.models import Venta, Empresa, Cliente, DetalleVenta
from api.services.facturacion_service import FacturacionService


def reset_venta_para_reemision(venta):
    """Resetea una venta a Borrador para permitir re-emisión."""
    venta.estado_dte = 'Borrador'
    venta.codigo_generacion = None
    venta.numero_control = None
    venta.sello_recepcion = None
    venta.save()
    print(f"   Venta ID {venta.id} reseteada a Borrador")


def emitir_venta(venta, servicio):
    """Emite una venta a MH y retorna el resultado."""
    try:
        resultado = servicio.procesar_factura(venta)
        return resultado
    except Exception as e:
        return {"exito": False, "mensaje": str(e), "errores": [str(e)]}


def main():
    print("="*60)
    print("CREAR FACTURAS Y VALIDAR CON MH")
    print("="*60)

    ventas = Venta.objects.select_related('empresa', 'cliente').order_by('-id')[:5]
    if not ventas:
        print("ERROR: No hay ventas en la base de datos.")
        return

    print(f"\nVentas encontradas: {ventas.count()}")

    # Resetear las últimas 2 ventas para re-emisión
    ventas_a_probar = list(ventas[:2])
    for v in ventas_a_probar:
        print(f"\nReseteando Venta ID {v.id} (Cliente: {v.cliente.nombre if v.cliente else 'N/A'})...")
        reset_venta_para_reemision(v)

    # Emitir cada una a MH
    resultados = []
    for venta in ventas_a_probar:
        print(f"\n--- Emitiendo Venta ID {venta.id} ({venta.tipo_venta}) ---")
        servicio = FacturacionService(venta.empresa)
        resultado = emitir_venta(venta, servicio)
        resultados.append((venta, resultado))

        if resultado.get('exito'):
            print(f"   OK - ACEPTADA POR MH")
            print(f"   Sello: {resultado.get('sello_recibido', 'N/A')[:50]}...")
        else:
            print(f"   FALLO - {resultado.get('mensaje', 'Error desconocido')}")
            if resultado.get('observaciones'):
                for obs in resultado.get('observaciones', [])[:5]:
                    print(f"      - {obs}")

    # Resumen
    print("\n" + "="*60)
    exitosas = sum(1 for _, r in resultados if r.get('exito'))
    print(f"RESUMEN: {exitosas}/{len(resultados)} facturas aceptadas por MH")
    print("="*60)


if __name__ == "__main__":
    main()
