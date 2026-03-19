"""
Script de prueba INDEPENDIENTE (sin Django) para validar credenciales MH.
Prueba los dos ambientes (Producción y Pruebas) con las credenciales dadas.

Ejecutar dentro del contenedor:
  docker compose -f docker-compose.prod.yml exec backend python test_mh_auth.py

O en cualquier máquina con Python + requests instalado:
  python3 test_mh_auth.py
"""
import requests

# ──────────────────────────────────────────
# CONFIGURAR AQUÍ LAS CREDENCIALES REALES
# ──────────────────────────────────────────
USER = "12092310921022"     # NIT sin guiones
PWD  = "2Caballo.Azul"     # Contraseña exacta (sensible a mayúsculas)
# ──────────────────────────────────────────

AMBIENTES = {
    "PRODUCCION (00)": "https://api.dtes.mh.gob.sv/seguridad/auth",
    "PRUEBAS    (01)": "https://apitest.dtes.mh.gob.sv/seguridad/auth",
}

HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "Mozilla/5.0",
}


def probar(nombre, url):
    print(f"\n{'─'*55}")
    print(f"  Ambiente : {nombre}")
    print(f"  URL      : {url}")
    print(f"  user     : {repr(USER)}")
    print(f"  pwd      : {repr(PWD)}   (len={len(PWD)})")
    print(f"{'─'*55}")
    try:
        r = requests.post(url, data={"user": USER, "pwd": PWD}, headers=HEADERS, timeout=20)
        print(f"  HTTP     : {r.status_code}")
        try:
            data = r.json()
            estado = data.get("body", {}).get("estado") or data.get("status")
            token  = data.get("body", {}).get("token")
            codigo = data.get("body", {}).get("codigoMsg")
            desc   = data.get("body", {}).get("descripcionMsg")
            if token:
                print(f"  ✅ TOKEN OBTENIDO  (len={len(token)})")
            else:
                print(f"  ❌ SIN TOKEN")
                print(f"     estado   = {estado}")
                print(f"     codigo   = {codigo}")
                print(f"     mensaje  = {desc}")
            print(f"  Respuesta completa: {data}")
        except Exception:
            print(f"  Respuesta (texto): {r.text[:300]}")
    except Exception as e:
        print(f"  ❌ ERROR DE CONEXIÓN: {e}")


if __name__ == "__main__":
    print("\n========================================")
    print("  TEST DE CREDENCIALES MH - AGILDTE")
    print("========================================")
    for nombre, url in AMBIENTES.items():
        probar(nombre, url)
    print("\n")
