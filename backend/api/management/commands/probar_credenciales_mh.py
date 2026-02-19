"""
Diagnostica las credenciales MH de una empresa.
Muestra el valor real (repr) para detectar espacios u otros caracteres ocultos.

Uso (desde backend/ o dentro del contenedor):
  python manage.py probar_credenciales_mh
  python manage.py probar_credenciales_mh --empresa 1

Con Docker:
  docker compose -f docker-compose.prod.yml exec backend python manage.py probar_credenciales_mh
"""
from django.core.management.base import BaseCommand

from api.models import Empresa


def mask(s, show=3):
    """Muestra primeros y últimos N caracteres, resto oculto."""
    if not s or len(s) <= show * 2:
        return "***"
    return f"{s[:show]}...{s[-show:]}"


class Command(BaseCommand):
    help = "Diagnostica credenciales MH: muestra valores (repr) y prueba autenticación"

    def add_arguments(self, parser):
        parser.add_argument(
            "--empresa",
            type=int,
            default=None,
            help="ID de empresa (por defecto la primera)",
        )

    def handle(self, *args, **options):
        emp_id = options.get("empresa")
        if emp_id:
            try:
                empresa = Empresa.objects.get(pk=emp_id)
            except Empresa.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Empresa ID {emp_id} no existe."))
                return
        else:
            empresa = Empresa.objects.first()
            if not empresa:
                self.stdout.write(self.style.ERROR("No hay empresas en la BD."))
                return

        self.stdout.write(self.style.WARNING("\n⚠️  Este comando muestra credenciales. Ejecutar solo en entorno seguro.\n"))
        self.stdout.write(f"🏢 Empresa: {empresa.nombre} (ID {empresa.id})")
        self.stdout.write("-" * 50)

        user_raw = empresa.user_api_mh or ""
        pwd_raw = empresa.clave_api_mh or ""

        user_stripped = user_raw.strip()
        pwd_stripped = pwd_raw.strip()

        self.stdout.write("\n📋 DIAGNÓSTICO (repr para ver caracteres ocultos):")
        self.stdout.write(f"   user_api_mh   = {repr(user_raw)}")
        self.stdout.write(f"                 len={len(user_raw)}, tras strip={len(user_stripped)}")
        self.stdout.write(f"   clave_api_mh  = {repr(pwd_raw)}")
        self.stdout.write(f"                 len={len(pwd_raw)}, tras strip={len(pwd_stripped)}")

        if user_raw != user_stripped or pwd_raw != pwd_stripped:
            self.stdout.write(self.style.WARNING("\n⚠️  HAY ESPACIOS O CARACTERES EXTRA. Tras strip:"))
            self.stdout.write(f"   user_stripped = {repr(user_stripped)}")
            self.stdout.write(f"   pwd_stripped  = {repr(pwd_stripped)}")

        if not user_stripped or not pwd_stripped:
            self.stdout.write(self.style.ERROR("\n❌ Credenciales vacías tras strip. Configúralas en Admin."))
            return

        self.stdout.write(f"\n📤 Valores que se enviarían a MH (enmascarados):")
        self.stdout.write(f"   user = {mask(user_stripped)} (len={len(user_stripped)})")
        self.stdout.write(f"   pwd  = {mask(pwd_stripped)} (len={len(pwd_stripped)})")

        self.stdout.write("\n🔐 Probando autenticación con MH...")
        try:
            from api.services.facturacion_service import FacturacionService, AutenticacionMHError

            svc = FacturacionService(empresa)
            token = svc.obtener_token()
            if token:
                self.stdout.write(self.style.SUCCESS(f"\n✅ Autenticación OK. Token obtenido (len={len(token)})."))
            else:
                self.stdout.write(self.style.ERROR("\n❌ MH no devolvió token."))
        except AutenticacionMHError as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Error de autenticación: {e}"))
            self.stdout.write("\n💡 Sugerencia: Compara repr(user) y repr(pwd) con los valores")
            self.stdout.write("   correctos. Si ves espacios o caracteres extra, ejecuta:")
            self.stdout.write("   python manage.py corregir_credenciales_db strip")
            self.stdout.write("   O edita la empresa en Admin y vuelve a guardar (guarda sin espacios).")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Error: {e}"))

        self.stdout.write("")
