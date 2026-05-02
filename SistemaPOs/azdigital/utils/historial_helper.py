# Programador: Oscar Amaya Romero
"""Helper para registrar acciones en el historial de usuarios (usa sesión y request de Flask)."""
from __future__ import annotations


def registrar_accion(cur, evento: str, detalle: str | None = None) -> None:
    """
    Registra una acción en el historial. Obtiene usuario e IP del contexto Flask.
    Usar cuando ya tienes cursor activo (cur) antes del commit.
    """
    try:
        from flask import request, session

        from azdigital.repositories import historial_usuarios_repo

        uid = session.get("user_id")
        uname = session.get("username")
        ip = request.remote_addr if request else None
        ua = (request.user_agent.string[:500] if request and request.user_agent else None)
        historial_usuarios_repo.registrar(
            cur,
            evento,
            usuario_id=uid,
            username=uname,
            detalle=detalle,
            ip_address=ip,
            user_agent=ua,
        )
    except Exception:
        pass
