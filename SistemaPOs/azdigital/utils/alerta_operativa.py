# Programador: Oscar Amaya Romero
"""
Avisos operativos a ALERT_EMAIL (por defecto framncisco@gmail.com).

- Modo local: el ticket quedó solo en POS (sin código de generación / sync fallido).
- Contingencia MH: una empresa entra en emergencia por falla de Hacienda.
"""
from __future__ import annotations

import logging
import os
import re
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

logger = logging.getLogger(__name__)

DESTINO_DEFAULT = "framncisco@gmail.com"
COOLDOWN_SEG = int(os.environ.get("ALERT_COOLDOWN_SEG", "1800") or "1800")
CLAVE_MODO_LOCAL = "modo_local"
CLAVE_CONTINGENCIA = "contingencia"


def _destino() -> str:
    return (os.environ.get("ALERT_EMAIL") or DESTINO_DEFAULT).strip() or DESTINO_DEFAULT


def _state_dir() -> Path:
    raw = (os.environ.get("ALERT_STATE_DIR") or "").strip()
    p = Path(raw) if raw else Path("/tmp/agildte_alertas")
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        p = Path("/tmp")
    return p


def _debe_enviar(clave: str, cooldown: int | None = None) -> bool:
    wait = COOLDOWN_SEG if cooldown is None else int(cooldown)
    path = _state_dir() / f"{clave}.ts"
    now = time.time()
    try:
        if path.exists() and (now - path.stat().st_mtime) < wait:
            return False
        path.write_text(str(int(now)), encoding="utf-8")
        return True
    except Exception:
        return True


def _smtp_cfg() -> dict | None:
    host = (os.environ.get("EMAIL_HOST") or "").strip()
    user = (os.environ.get("EMAIL_HOST_USER") or "").strip()
    if not host or not user:
        return None
    from_address = (os.environ.get("EMAIL_FROM_ADDRESS") or "").strip() or user
    return {
        "host": host,
        "port": int(os.environ.get("EMAIL_PORT") or "587"),
        "user": user,
        "password": os.environ.get("EMAIL_HOST_PASSWORD") or "",
        "use_tls": (os.environ.get("EMAIL_USE_TLS") or "true").lower() in ("1", "true", "yes"),
        "from_address": from_address,
    }


def _enviar_smtp(asunto: str, cuerpo: str) -> bool:
    cfg = _smtp_cfg()
    destino = _destino()
    if not cfg:
        logger.warning("Alerta operativa no enviada (sin EMAIL_HOST/EMAIL_HOST_USER): %s", asunto)
        return False
    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"] = cfg["from_address"]
    msg["To"] = destino
    html = (
        "<p>POS AgilDTE / AgilDTE</p>"
        f"<pre style='font-family:system-ui,sans-serif;white-space:pre-wrap'>{cuerpo}</pre>"
        "<p style='color:#666;font-size:12px'>Aviso automático del servidor.</p>"
    )
    msg.attach(MIMEText(cuerpo, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    try:
        if cfg["use_tls"]:
            server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=30)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            server = smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=30)
        if cfg["password"]:
            server.login(cfg["user"], cfg["password"])
        from_raw = cfg["from_address"]
        m = re.search(r"<([^>]+)>", from_raw)
        mail_from = m.group(1) if m else from_raw
        server.sendmail(mail_from, [destino], msg.as_string())
        server.quit()
        logger.info("Alerta operativa enviada a %s: %s", destino, asunto)
        return True
    except Exception:
        logger.exception("No se pudo enviar alerta operativa a %s", destino)
        return False


def alertar_modo_local(problema: str, detalle: str = "", *, forzar: bool = False) -> bool:
    """Ticket quedó solo en POS (sin código de generación / sync caído)."""
    if not forzar and not _debe_enviar(CLAVE_MODO_LOCAL):
        return False
    asunto = "POS AgilDTE está en modo local por problemas"
    cuerpo = (
        "POS AgilDTE está en modo local por problemas.\n\n"
        f"Problema: {problema.strip() or 'el ticket no obtuvo código de generación y quedó solo en el POS.'}\n"
    )
    if detalle.strip():
        cuerpo += f"\nDetalle:\n{detalle.strip()}\n"
    cuerpo += (
        "\nLas ventas se guardan en caja, pero no llegan a AgilDTE / MH "
        "hasta remitir o restablecer la sincronización.\n"
    )
    return _enviar_smtp(asunto, cuerpo)


def alertar_contingencia(
    *,
    empresa: str,
    motivo: str = "",
    origen: str = "POS/AgilDTE",
    forzar: bool = False,
) -> bool:
    """Una empresa entra en contingencia por falla de MH u otra emergencia."""
    clave = f"{CLAVE_CONTINGENCIA}:{(empresa or 'sin-empresa')[:40]}"
    if not forzar and not _debe_enviar(clave):
        return False
    asunto = f"Contingencia MH: {empresa or 'empresa'} (POS AgilDTE en modo local)"
    cuerpo = (
        "POS AgilDTE está en modo local por problemas.\n\n"
        f"Origen: {origen}\n"
        f"Empresa: {empresa or 'no indicada'}\n"
        f"Problema: contingencia por falla de MH u emergencia.\n"
    )
    if motivo.strip():
        cuerpo += f"Motivo: {motivo.strip()}\n"
    cuerpo += (
        "\nLos DTE se emiten en contingencia (respaldo local) hasta que Hacienda "
        "vuelva a estar disponible y se transmitan los pendientes.\n"
    )
    return _enviar_smtp(asunto, cuerpo)


def contar_tickets_sin_codigo(cur) -> tuple[int, list[tuple]]:
    cur.execute(
        """
        SELECT v.id, v.empresa_id, v.fecha_registro::date
        FROM ventas v
        WHERE COALESCE(v.estado, 'ACTIVO') = 'ACTIVO'
          AND TRIM(COALESCE(v.codigo_generacion, '')) = ''
          AND UPPER(COALESCE(v.tipo_comprobante, 'TICKET')) IN ('TICKET', 'FACTURA', 'CREDITO_FISCAL')
          AND v.fecha_registro >= (CURRENT_DATE - INTERVAL '14 days')
        ORDER BY v.id DESC
        LIMIT 30
        """
    )
    rows = cur.fetchall() or []
    cur.execute(
        """
        SELECT COUNT(*) FROM ventas v
        WHERE COALESCE(v.estado, 'ACTIVO') = 'ACTIVO'
          AND TRIM(COALESCE(v.codigo_generacion, '')) = ''
          AND UPPER(COALESCE(v.tipo_comprobante, 'TICKET')) IN ('TICKET', 'FACTURA', 'CREDITO_FISCAL')
          AND v.fecha_registro >= (CURRENT_DATE - INTERVAL '14 days')
        """
    )
    n = int((cur.fetchone() or [0])[0] or 0)
    return n, rows


def vigilar_tickets_locales() -> None:
    """Si hay tickets recientes sin código DTE, avisa por correo (con cooldown)."""
    try:
        import psycopg2
        from database import ConexionDB
    except Exception:
        return
    conn = None
    try:
        db = ConexionDB()
        conn = psycopg2.connect(**db.config)
        cur = conn.cursor()
        n, rows = contar_tickets_sin_codigo(cur)
        cur.close()
        if n <= 0:
            return
        muestra = ", ".join(f"#{r[0]}" for r in rows[:12])
        alertar_modo_local(
            f"Hay {n} ticket(s) de los últimos 14 días sin código de generación (solo en POS).",
            detalle=f"Ejemplos: {muestra}",
        )
    except Exception:
        logger.exception("Vigilancia de tickets locales falló")
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
