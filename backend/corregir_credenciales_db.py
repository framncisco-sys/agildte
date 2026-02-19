"""
Script para corregir credenciales en la BD.
- limpiar_datos(): Actualiza una empresa con valores correctos (manual)
- limpiar_espacios_todas(): Recorre todas las empresas y aplica strip() a credenciales (sin cambiar valores)
"""
import os
import django

# 1. Configurar entorno Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_contable.settings')
django.setup()

from api.models import Empresa

def limpiar_espacios_todas():
    """Recorre todas las empresas y guarda (el save() del modelo aplica strip a credenciales)."""
    print("🧹 Limpiando espacios en credenciales de todas las empresas...")
    count = 0
    for emp in Empresa.objects.all():
        emp.save()
        count += 1
        print(f"   ✅ {emp.nombre} (ID {emp.id})")
    print(f"✨ {count} empresa(s) actualizada(s).")

def limpiar_datos():
    print("🧹 INICIANDO LIMPIEZA DE CREDENCIALES...")
    
    # Datos CORRECTOS (Copiados del script que funcionó)
    USUARIO_CORRECTO = "12092310921022"
    CLAVE_CORRECTA   = "2Caballo.azul"
    
    # Obtener tu empresa (asumimos que es la primera o única)
    empresa = Empresa.objects.first()
    
    if not empresa:
        print("❌ No se encontró ninguna empresa creada.")
        return

    print(f"🏢 Empresa encontrada: {empresa.nombre}")
    
    # DIAGNÓSTICO: Mostrar qué está guardado realmente (usando repr para ver espacios ocultos)
    print(f"   Datos actuales (SUCIO): User='{empresa.user_api_mh}' | Clave='{empresa.clave_api_mh}'")
    
    # CORRECCIÓN
    empresa.user_api_mh = USUARIO_CORRECTO
    empresa.clave_api_mh = CLAVE_CORRECTA
    empresa.ambiente = '00' # Aseguramos que sea PRUEBAS
    empresa.save()
    
    print("-" * 40)
    print(f"✅ Datos nuevos (LIMPIO): User='{empresa.user_api_mh}' | Clave='{empresa.clave_api_mh}'")
    print("✨ Base de datos actualizada correctamente.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "strip":
        limpiar_espacios_todas()
    else:
        limpiar_datos()