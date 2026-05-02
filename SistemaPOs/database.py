# Programador: Oscar Amaya Romero
import os

import psycopg2

from azdigital.utils.env_config import postgres_connection_kwargs


class ConexionDB:
    def __init__(self):
        # DATABASE_URL (PaaS) o AZ_DB_*; ver azdigital/utils/env_config.py
        self.config = postgres_connection_kwargs()

    def ejecutar_sql(self, query, params=None, es_select=False):
        conn = None
        try:
            conn = psycopg2.connect(**self.config)
            # Refuerza client encoding por si el server ignora options.
            try:
                conn.set_client_encoding(os.environ.get("AZ_DB_CLIENT_ENCODING", "UTF8"))
            except Exception:
                pass
            cur = conn.cursor()
            cur.execute(query, params)
            
            res = None
            if es_select:
                # Si la consulta es un SELECT o tiene RETURNING, usamos fetchall
                res = cur.fetchall()
            else:
                # Si es un INSERT/UPDATE, guardamos los cambios
                conn.commit()
                res = True
            
            cur.close()
            conn.close()
            return res
        except Exception as e:
            if conn:
                conn.rollback()
                conn.close()
            try:
                msg = str(e)
            except Exception:
                msg = repr(e)
            print(f"Aviso de AZ DIGITAL (Error SQL): {msg}")
            return [] if es_select else None


def conectar():
    """
    Conexión simple para scripts legacy (Tkinter).
    Preferir `ConexionDB().ejecutar_sql(...)` en la app web.
    """
    try:
        client_encoding = os.environ.get("AZ_DB_CLIENT_ENCODING", "UTF8")
        cfg = postgres_connection_kwargs()
        conn = psycopg2.connect(**cfg)
        try:
            conn.set_client_encoding(client_encoding)
        except Exception:
            pass
        return conn
    except Exception as e:
        try:
            msg = str(e)
        except Exception:
            msg = repr(e)
        print(f"Aviso de AZ DIGITAL (Error conectar): {msg}")
        return None