"""
Prueba STANDALONE: detecta qué valor de 'ambiente' acepta MH en el endpoint recepciondte.
No requiere Django ni base de datos. Solo necesita requests.

Ejecutar:
  cd backend
  venv\Scripts\python test_ambiente_mh.py         (Windows)
  venv/bin/python test_ambiente_mh.py             (Linux/Mac)
"""
import requests
import json
import uuid
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURA AQUÍ
# ─────────────────────────────────────────────
USER_MH = "12092310921022"
PWD_MH  = "2Caballo.Azul"
# ─────────────────────────────────────────────

URL_AUTH     = "https://apitest.dtes.mh.gob.sv/seguridad/auth"
URL_RECEPCION = "https://apitest.dtes.mh.gob.sv/fesv/recepciondte"

print("=" * 60)
print("TEST AMBIENTE MH - apitest.dtes.mh.gob.sv")
print("=" * 60)

# PASO 1: Obtener token
print("\n[1] Autenticando...")
r = requests.post(
    URL_AUTH,
    data={"user": USER_MH, "pwd": PWD_MH},
    headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "Mozilla/5.0"},
    timeout=30
)
print(f"    Status: {r.status_code}")
datos_auth = r.json()
token = datos_auth.get("body", {}).get("token")

if not token:
    print(f"❌ Auth FALLÓ: {datos_auth}")
    exit(1)

print(f"✅ Token obtenido (primeros 30 chars): {token[:30]}...")

# PASO 2: Probar envío con diferentes valores de ambiente
# Un DTE falso (será rechazado por datos inválidos, pero podemos ver si el
# campo 'ambiente' pasa o da VALOR NO VALIDO)
print("\n[2] Probando valores de 'ambiente' en el envelope de envío...")
print("    (El DTE es inválido a propósito — sólo nos interesa si 'ambiente' es aceptado)")

for valor_ambiente in ["00", "01"]:
    fake_dte = "FAKE_JWS_PARA_TEST"
    codigo_gen = str(uuid.uuid4()).upper()

    payload = {
        "ambiente": valor_ambiente,
        "idEnvio": 1,
        "version": 1,
        "tipoDte": "01",
        "documento": fake_dte,
        "codigoGeneracion": codigo_gen
    }

    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    r2 = requests.post(URL_RECEPCION, json=payload, headers=headers, timeout=30)
    try:
        resp_json = r2.json()
    except Exception:
        resp_json = {"raw": r2.text}

    observaciones = resp_json.get("observaciones", [])
    descripcion   = resp_json.get("descripcionMsg", "")
    estado        = resp_json.get("estado", "")

    # Si dice "VALOR NO VALIDO" en las observaciones → ese ambiente es incorrecto
    ambiente_invalido = any("VALOR NO VALIDO" in str(o) for o in observaciones)

    print(f"\n  ambiente='{valor_ambiente}' → HTTP {r2.status_code}")
    print(f"    estado:      {estado}")
    print(f"    descripcion: {descripcion}")
    print(f"    observaciones: {observaciones}")

    if ambiente_invalido:
        print(f"    ❌ Este valor de ambiente es RECHAZADO por MH")
    else:
        print(f"    ✅ Este valor de ambiente es ACEPTADO por MH (el DTE es inválido pero ambiente OK)")

print("\n" + "=" * 60)
print("FIN DEL TEST")
print("=" * 60)
