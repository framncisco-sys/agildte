"""DEPRECADO: Use configurar_admin_unico.py en su lugar.
El único superusuario es: admin / 123456789"""
import subprocess
import sys
import os
print("Redirigiendo a configurar_admin_unico.py ...\n")
subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "configurar_admin_unico.py")])
