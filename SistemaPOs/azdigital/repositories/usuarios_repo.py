# Programador: Oscar Amaya Romero
from __future__ import annotations


def get_usuario_login(cur, username: str):
    cur.execute(
        """
        SELECT u.id, u.username, u.password_hash, u.rol, u.sucursal_id
        FROM usuarios u
        WHERE LOWER(TRIM(u.username)) = LOWER(TRIM(%s)) AND u.activo = TRUE
        """,
        (username.strip(),),
    )
    row = cur.fetchone()
    if not row:
        return None
    empresa_id = 1
    sucursal_id = row[4] if len(row) > 4 else row[3]  # sucursal_id
    if sucursal_id:
        cur.execute("SELECT empresa_id FROM sucursales WHERE id = %s", (sucursal_id,))
        r = cur.fetchone()
        if r:
            empresa_id = r[0] or 1
    try:
        cur.execute("SELECT empresa_id FROM usuarios WHERE id = %s", (row[0],))
        r = cur.fetchone()
        if r and r[0]:
            empresa_id = r[0]
    except Exception:
        pass
    return row + (empresa_id,)


def listar_usuarios(cur, empresa_id: int = None):
    """Solo usuarios que pertenecen a la empresa: u.empresa_id = X O su sucursal.empresa_id = X.
    Excluye usuarios huérfanos (sin empresa ni sucursal) para evitar que vean datos de otras empresas."""
    if empresa_id:
        cur.execute(
            """
            SELECT u.id, u.username, u.rol, COALESCE(s.nombre, ''), u.activo
            FROM usuarios u
            LEFT JOIN sucursales s ON s.id = u.sucursal_id
            WHERE (u.empresa_id = %s) OR (s.empresa_id = %s)
            ORDER BY u.id DESC
            """,
            (empresa_id, empresa_id),
        )
    else:
        cur.execute(
            """
            SELECT u.id, u.username, u.rol, COALESCE(s.nombre, ''), u.activo
            FROM usuarios u
            LEFT JOIN sucursales s ON s.id = u.sucursal_id
            ORDER BY u.id DESC
            """
        )
    return cur.fetchall()


def listar_usuarios_todos(cur):
    """Todos los usuarios con nombre de empresa. Para superusuario."""
    try:
        cur.execute(
            """
            SELECT u.id, u.username, u.rol, COALESCE(s.nombre, ''), u.activo,
                   COALESCE(e.nombre_comercial, e.nombre, '—')
            FROM usuarios u
            LEFT JOIN sucursales s ON s.id = u.sucursal_id
            LEFT JOIN empresas e ON e.id = COALESCE(u.empresa_id, s.empresa_id)
            ORDER BY u.id DESC
            """
        )
        return cur.fetchall()
    except Exception:
        cur.execute(
            """
            SELECT u.id, u.username, u.rol, COALESCE(s.nombre, ''), u.activo, '—'
            FROM usuarios u
            LEFT JOIN sucursales s ON s.id = u.sucursal_id
            ORDER BY u.id DESC
            """
        )
        return cur.fetchall()


def get_usuario(cur, usuario_id: int):
    try:
        cur.execute(
            "SELECT id, username, rol, sucursal_id, empresa_id FROM usuarios WHERE id = %s",
            (usuario_id,),
        )
        return cur.fetchone()
    except Exception:
        cur.execute(
            "SELECT id, username, rol, sucursal_id FROM usuarios WHERE id = %s",
            (usuario_id,),
        )
        row = cur.fetchone()
        if row:
            return row + (1,)  # empresa_id por defecto
        return None


def crear_usuario(cur, username: str, password_hash: str, rol: str, sucursal_id, empresa_id=None):
    suc = int(sucursal_id) if sucursal_id and str(sucursal_id).isdigit() else None
    emp = None if empresa_id is None else (int(empresa_id) if empresa_id and str(empresa_id).isdigit() and int(empresa_id) > 0 else 1)
    cur.execute(
        """
        INSERT INTO usuarios (username, password_hash, rol, sucursal_id, empresa_id, activo)
        VALUES (%s, %s, %s, %s, %s, TRUE)
        """,
        (username, password_hash, rol, suc, emp),
    )


def actualizar_usuario(cur, usuario_id: int, username: str, password_hash: str | None, rol: str, sucursal_id, empresa_id=None) -> None:
    suc = int(sucursal_id) if sucursal_id and str(sucursal_id).isdigit() else None
    emp = None if empresa_id is None else (int(empresa_id) if empresa_id and str(empresa_id).isdigit() and int(empresa_id) > 0 else 1)
    try:
        if password_hash:
            cur.execute(
                "UPDATE usuarios SET username = %s, password_hash = %s, rol = %s, sucursal_id = %s, empresa_id = %s WHERE id = %s",
                (username, password_hash, rol, suc, emp, usuario_id),
            )
        else:
            cur.execute(
                "UPDATE usuarios SET username = %s, rol = %s, sucursal_id = %s, empresa_id = %s WHERE id = %s",
                (username, rol, suc, emp, usuario_id),
            )
    except Exception:
        # Fallback solo si empresa_id no es NULL (ej. columna empresa_id no existe en esquemas antiguos)
        if emp is not None:
            if password_hash:
                cur.execute(
                    "UPDATE usuarios SET username = %s, password_hash = %s, rol = %s, sucursal_id = %s WHERE id = %s",
                    (username, password_hash, rol, suc, usuario_id),
                )
            else:
                cur.execute(
                    "UPDATE usuarios SET username = %s, rol = %s, sucursal_id = %s WHERE id = %s",
                    (username, rol, suc, usuario_id),
                )
        else:
            raise


def eliminar_usuario(cur, usuario_id: int) -> bool:
    cur.execute("UPDATE usuarios SET activo = FALSE WHERE id = %s", (usuario_id,))
    return cur.rowcount > 0


def actualizar_password(cur, user_id: int, password_hash: str) -> None:
    cur.execute(
        "UPDATE usuarios SET password_hash = %s WHERE id = %s",
        (password_hash, user_id),
    )

