"""Avisos operativos (modo local POS / contingencia MH) a ALERT_EMAIL."""
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


def _debe_enviar(clave: str) -> bool:
    path = _state_dir() / f"{clave}.ts"
    now = time.time()
    try:
        if path.exists() and (now - path.stat().st_mtime) < COOLDOWN_SEG:
            return False
        path.write_text(str(int(now)), encoding="utf-8")
        return True
    except Exception:
        return True


def enviar_alerta_operativa(asunto: str, cuerpo: str, *, clave: str = "ops") -> bool:
    """Envía correo de alerta (SES API si hay AWS, si no SMTP EMAIL_*). No lanza."""
    if not _debe_enviar(clave):
        return False
    destino = _destino()
    from_address = (
        os.environ.get("EMAIL_FROM_ADDRESS", "").strip()
        or os.environ.get("EMAIL_HOST_USER", "").strip()
    )
    if not from_address:
        logger.warning("Alerta operativa sin EMAIL_FROM_ADDRESS/EMAIL_HOST_USER")
        return False
    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"] = from_address
    msg["To"] = destino
    msg.attach(MIMEText(cuerpo, "plain", "utf-8"))
    html = f"<pre style='white-space:pre-wrap;font-family:system-ui,sans-serif'>{cuerpo}</pre>"
    msg.attach(MIMEText(html, "html", "utf-8"))
    raw_bytes = msg.as_bytes() if hasattr(msg, "as_bytes") else msg.as_string().encode("utf-8")

    key = os.environ.get("AWS_ACCESS_KEY_ID", "").strip()
    secret = os.environ.get("AWS_SECRET_ACCESS_KEY", "").strip()
    if key and secret:
        try:
            import boto3

            region = (
                os.environ.get("AWS_REGION", "").strip()
                or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
            )
            boto3.client("ses", region_name=region).send_raw_email(
                Source=from_address,
                Destinations=[destino],
                RawMessage={"Data": raw_bytes},
            )
            logger.info("Alerta operativa SES a %s: %s", destino, asunto)
            return True
        except Exception:
            logger.exception("SES API falló para alerta operativa; se intenta SMTP")

    host = os.environ.get("EMAIL_HOST", "").strip()
    user = os.environ.get("EMAIL_HOST_USER", "").strip()
    if not host or not user:
        logger.warning("Alerta operativa: sin SMTP")
        return False
    try:
        port = int(os.environ.get("EMAIL_PORT", "587"))
        use_tls = os.environ.get("EMAIL_USE_TLS", "true").lower() in ("1", "true", "yes")
        password = os.environ.get("EMAIL_HOST_PASSWORD", "")
        if use_tls:
            server = smtplib.SMTP(host, port, timeout=30)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            server = smtplib.SMTP_SSL(host, port, timeout=30)
        if password:
            server.login(user, password)
        m = re.search(r"<([^>]+)>", from_address)
        mail_from = m.group(1) if m else from_address
        server.sendmail(mail_from, [destino], msg.as_string())
        server.quit()
        logger.info("Alerta operativa SMTP a %s: %s", destino, asunto)
        return True
    except Exception:
        logger.exception("No se pudo enviar alerta operativa SMTP")
        return False


def alertar_contingencia_empresa(empresa, motivo: str = "") -> bool:
    nombre = getattr(empresa, "nombre", None) or getattr(empresa, "nombre_comercial", None) or str(empresa)
    eid = getattr(empresa, "id", "")
    asunto = f"Contingencia MH: {nombre} (POS AgilDTE en modo local)"
    cuerpo = (
        "POS AgilDTE está en modo local por problemas.\n\n"
        f"Origen: AgilDTE (portal)\n"
        f"Empresa: {nombre} (id {eid})\n"
        "Problema: contingencia por falla de MH u emergencia.\n"
    )
    if (motivo or "").strip():
        cuerpo += f"Motivo: {motivo.strip()}\n"
    cuerpo += (
        "\nLos DTE de esta empresa se emiten en contingencia hasta transmitir pendientes a Hacienda.\n"
    )
    return enviar_alerta_operativa(asunto, cuerpo, clave=f"contingencia:{eid}")
