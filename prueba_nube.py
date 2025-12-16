import requests

# TU URL DE RAILWAY (La que usaste en el navegador)
url = 'https://backend-production-8f98.up.railway.app/api/clientes/'

# Los datos de un cliente ficticio (Simulando lo que vendría en el JSON)
datos_cliente = {
    "nombre": "Ferreteria El Buen Martillo S.A.",
    "nit": "0614-010190-102-1",
    "nrc": "123456-7",  # <--- ¡AGREGA ESTA LÍNEA!
    "direccion": "San Miguel, Centro",
    "clave_correo": "ferreteria_martillo",
    "telefono": "2660-1234"
}

print(f"📡 Enviando datos a: {url} ...")

try:
    response = requests.post(url, json=datos_cliente)

    if response.status_code == 201:
        print("✅ ¡ÉXITO! Cliente creado correctamente en la nube.")
        print("Respuesta del servidor:", response.json())
    else:
        print("⚠️ Hubo un problema.")
        print(f"Status: {response.status_code}")
        print("Error:", response.text)

except Exception as e:
    print("❌ Error de conexión:", e)