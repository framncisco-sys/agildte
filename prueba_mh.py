import requests
import json

def obtener_token_mh():
    # ---------------------------------------------------------
    # CORRECCIÓN IMPORTANTE: Usar la URL de PRUEBAS (apitest)
    # ---------------------------------------------------------
    url_auth = "https://apitest.dtes.mh.gob.sv/seguridad/auth" 
    
    # Tu usuario correcto según la foto
    usuario = "12092310921022"
    
    # Tu contraseña (asegúrate que sea la última que guardaste)
    clave = "2Caballoblanco.verde" 

    payload = { "user": usuario, "pwd": clave }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0'
    }

    print(f"🔌 Conectando al ambiente de PRUEBAS (apitest)...")
    print(f"   Usuario: {usuario}")
    
    try:
        response = requests.post(url_auth, data=payload, headers=headers)

        if response.status_code == 200:
            datos = response.json()
            token = datos.get("body", {}).get("token")
            
            if token:
                print("\n✅ ¡SÍ! TOKEN RECIBIDO EXITOSAMENTE.")
                print(f"Token: {token[:50]}...")
                return token
            else:
                print(f"\n⚠️ Respuesta inesperada: {datos}")
        else:
            print(f"\n❌ Error {response.status_code}: {response.text}")

    except Exception as e:
        print(f"\n❌ Error: {e}")

obtener_token_mh()