"""
Configura el cliente de la última venta CCF como gran contribuyente + mismo giro
para probar IVA Percibido 1% (ivaPerci1 = 1.23 en subTotal 123).
"""
import os
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_contable.settings')
import django
django.setup()

from api.models import Venta, Cliente

venta = Venta.objects.filter(tipo_venta='CCF').select_related('cliente', 'empresa').last()
if not venta or not venta.cliente:
    print("No hay venta CCF con cliente.")
    sys.exit(1)

cliente = venta.cliente
empresa = venta.empresa
cod_empresa = empresa.cod_actividad or '70200'

cliente.gran_contribuyente = True
cliente.cod_actividad = cod_empresa
cliente.save()
print(f"OK - Cliente {cliente.nombre} (ID {cliente.id}):")
print(f"   gran_contribuyente=True, cod_actividad={cod_empresa} (mismo giro que empresa)")
