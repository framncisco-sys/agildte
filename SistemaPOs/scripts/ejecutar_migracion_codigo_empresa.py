# Programador: Oscar Amaya Romero
"""Ejecuta la migración para permitir códigos de producto repetidos por empresa.
   Ejecutar: python scripts/ejecutar_migracion_codigo_empresa.py"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Cargar .env si existe (igual que app.py)
def _load_dotenv(path=".env"):
    try:
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), path)
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip('"').strip("'")
                    if k and (k not in os.environ or not os.environ.get(k)):
                        os.environ[k] = v
    except FileNotFoundError:
        pass

def main():
    _load_dotenv()
    from database import ConexionDB
    import psycopg2
    db = ConexionDB()
    conn = cur = None
    try:
        conn = psycopg2.connect(**db.config)
        cur = conn.cursor()
        cur.execute("ALTER TABLE productos DROP CONSTRAINT IF EXISTS productos_codigo_barra_key")
        cur.execute("ALTER TABLE productos DROP CONSTRAINT IF EXISTS productos_empresa_codigo_uniq")
        cur.execute("""
            ALTER TABLE productos ADD CONSTRAINT productos_empresa_codigo_uniq 
            UNIQUE (empresa_id, codigo_barra)
        """)
        conn.commit()
        print("OK: Migración aplicada. Cada empresa puede tener sus propios códigos de producto.")
    except Exception as e:
        print("Error:", e)
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
