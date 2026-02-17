import os
import sys
import django

# Configurar encoding para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# 1. Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_contable.settings')
django.setup()

from api.models import Venta, Empresa
from api.services.facturacion_service import FacturacionService

def probar_emision():
    print("INICIANDO PRUEBA DE EMISION REAL (ARQUITECTURA SAAS)...")
    
    try:
        # 2. Buscar la última venta creada
        venta = Venta.objects.last()
        if not venta:
            print("ERROR: No hay ventas en la base de datos. Crea una en el Admin primero.")
            return

        cliente_nombre = venta.cliente.nombre if venta.cliente else "Consumidor Final"
        print(f"Procesando Venta ID: {venta.id} | Cliente: {cliente_nombre} | Tipo: {venta.tipo_venta}")
        
        # 3. Instanciar el Servicio con la Empresa de la venta
        # Esto cargará automáticamente las credenciales que guardaste en el Admin
        servicio = FacturacionService(venta.empresa)
        
        # 4. ¡DISPARAR!
        resultado = servicio.procesar_factura(venta)
        
        # 5. Ver resultados
        if resultado['exito']:
            print("\n" + "="*50)
            print("EXITO TOTAL! FACTURA ACEPTADA POR HACIENDA")
            print("="*50)
            print(f"Sello de Recepcion: {resultado['sello_recibido']}")
            print(f"Codigo Generacion: {venta.codigo_generacion}")
            print(f"Empresa Emisora: {venta.empresa.nombre}")
            print("="*50)
            print("Nota: Verifica en el Admin de Django, la venta debe tener el sello guardado.")
        else:
            print("\nLA FACTURA FUE RECHAZADA O HUBO ERROR:")
            print(f"Error: {resultado.get('error')}")
            print(f"Detalle: {resultado.get('mensaje')}")

    except Exception as e:
        print(f"\nError Critico del Script: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    probar_emision()