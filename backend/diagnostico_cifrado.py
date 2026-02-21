"""
Script de diagnóstico para verificar el estado del cifrado en BD.
Ejecutar dentro del contenedor:
  docker compose -f docker-compose.prod.yml exec backend python diagnostico_cifrado.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_contable.settings')
django.setup()

from api.models import Empresa
from api.utils.encryption import _get_fernet

print("=" * 60)
print("DIAGNÓSTICO DE CIFRADO Y CREDENCIALES MH")
print("=" * 60)

fernet = _get_fernet()
print(f"\n[1] Fernet inicializado: {fernet is not None}")

emp = Empresa.objects.first()
if not emp:
    print("❌ No hay ninguna empresa en BD.")
    exit(1)

print(f"\n[2] Empresa: {emp.nombre} (ID {emp.id})")
print(f"    ambiente: {repr(emp.ambiente)}")

user = emp.user_api_mh
pwd  = emp.clave_api_mh

print(f"\n[3] user_api_mh:")
print(f"    repr  = {repr(user)}")
print(f"    len   = {len(user or '')}")

print(f"\n[4] clave_api_mh:")
print(f"    repr  = {repr(pwd)}")
print(f"    len   = {len(pwd or '')}")

# Si empieza con 'gAAAA' significa que from_db_value falló (devolvió el ciphertext)
es_cifrado_roto = (pwd or '').startswith('gAAAA')
print(f"\n[5] ¿Descifrado falló (devuelve ciphertext)?: {'SÍ ❌ - la SECRET_KEY o FERNET_KEY cambió' if es_cifrado_roto else 'NO ✅'}")

# Verificar si tiene espacios
tiene_espacio = pwd is not None and pwd != pwd.strip()
print(f"[6] ¿Tiene espacios al inicio/final?: {'SÍ ❌' if tiene_espacio else 'NO ✅'}")

print("\n" + "=" * 60)
print("RESULTADO:")
if es_cifrado_roto:
    print("⚠️  El descifrado falló. La clave de cifrado cambió.")
    print("   Solución: ejecutar el Paso 3 del diagnóstico para re-guardar.")
elif tiene_espacio:
    print("⚠️  La contraseña tiene espacios en BD.")
    print("   Solución: ejecutar el Paso 3 del diagnóstico.")
elif pwd == '2Caballo.Azul':
    print("✅ La contraseña en BD es correcta ('2Caballo.Azul').")
    print("   El problema puede estar en el cifrado del request HTTP a MH.")
else:
    print(f"⚠️  La contraseña en BD es: {repr(pwd)}")
    print("   Verifica si es la contraseña correcta.")
print("=" * 60)
