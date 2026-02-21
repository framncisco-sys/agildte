"""
Cambia el ambiente de la empresa a '01' (PRUEBAS / apitest.dtes.mh.gob.sv).
Ejecutar dentro del contenedor:
  docker compose -f docker-compose.prod.yml exec backend python fijar_ambiente_pruebas.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_contable.settings')
django.setup()

from api.models import Empresa

emp = Empresa.objects.first()
print(f"Empresa:         {emp.nombre} (ID {emp.id})")
print(f"Ambiente actual: {repr(emp.ambiente)}")

emp.ambiente = '01'   # '01' = PRUEBAS (apitest.dtes.mh.gob.sv)
emp.save(update_fields=['ambiente'])
emp.refresh_from_db()

print(f"Ambiente nuevo:  {repr(emp.ambiente)}")
print("✅ Listo. Ahora el sistema usará apitest.dtes.mh.gob.sv (PRUEBAS)")
