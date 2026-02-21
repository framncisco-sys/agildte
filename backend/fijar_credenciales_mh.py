"""
Fija las credenciales MH directamente en BD (con cifrado correcto).
Ejecutar dentro del contenedor:
  docker compose -f docker-compose.prod.yml exec backend python fijar_credenciales_mh.py

IMPORTANTE: Edita USER y PASSWORD abajo antes de ejecutar.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_contable.settings')
django.setup()

from api.models import Empresa

# ─────────────────────────────────────────────
# CONFIGURA AQUÍ LOS VALORES CORRECTOS
# ─────────────────────────────────────────────
EMPRESA_ID  = None          # None = primera empresa, o pon el ID: 1, 2, ...
USER_MH     = "12092310921022"
PASSWORD_MH = "2Caballo.Azul"   # Sin espacios al inicio/final
# ─────────────────────────────────────────────

print("=" * 60)
print("FIJANDO CREDENCIALES MH EN BD")
print("=" * 60)

if EMPRESA_ID:
    emp = Empresa.objects.get(pk=EMPRESA_ID)
else:
    emp = Empresa.objects.first()

if not emp:
    print("❌ No se encontró ninguna empresa.")
    exit(1)

print(f"\nEmpresa: {emp.nombre} (ID {emp.id})")
print(f"Antes - user: {repr(emp.user_api_mh)}")
print(f"Antes - pwd:  repr_primeros10={repr((emp.clave_api_mh or '')[:10])}")

# Asignar y guardar (save() hará strip() y get_prep_value cifrará)
emp.user_api_mh  = USER_MH.strip()
emp.clave_api_mh = PASSWORD_MH.strip()
emp.save(update_fields=['user_api_mh', 'clave_api_mh'])

# Verificar releyendo de BD
emp.refresh_from_db()
pwd_verificada = emp.clave_api_mh
user_verificado = emp.user_api_mh

print(f"\nDespués - user: {repr(user_verificado)}")
print(f"Después - pwd len={len(pwd_verificada or '')}")

ok_user = user_verificado == USER_MH.strip()
ok_pwd  = pwd_verificada == PASSWORD_MH.strip()

print("\n" + "=" * 60)
if ok_user and ok_pwd:
    print("✅ Credenciales guardadas y verificadas correctamente.")
    print("   Ya puedes quitar MH_PASSWORD_OVERRIDE del .env y reiniciar.")
else:
    print(f"❌ Verificación fallida:")
    print(f"   user OK: {ok_user}")
    print(f"   pwd  OK: {ok_pwd} (repr={repr(pwd_verificada)})")
    print("   ⚠️  Mantén MH_PASSWORD_OVERRIDE=2Caballo.Azul en .env por ahora.")
print("=" * 60)
