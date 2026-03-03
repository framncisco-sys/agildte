"""
Servicio de envío de correos con facturas (PDF + JSON/XML).
Incluye branding AgilDTE en el pie de cada correo.

Modos de envío (en orden de prioridad):
  1. SES API (boto3) — si AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY están definidos.
     Usa HTTPS (puerto 443), útil cuando SMTP 587/465 está bloqueado.
  2. SMTP — variables EMAIL_* o campos smtp_* del modelo Empresa.
"""
import json
import logging
import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from ..dte_generator import DTEGenerator
from ..utils.pdf_generator import generar_pdf_venta

logger = logging.getLogger(__name__)

AGILDTE_WEB_URL = "https://agildte.com"
BRANDING_HTML = f'''
<div style="margin-top: 30px; padding-top: 15px; border-top: 1px solid #eee; font-size: 11px; color: #888;">
  Facturado con <strong>AgilDTE</strong> - El sistema más rápido de facturación en El Salvador.
  <a href="{AGILDTE_WEB_URL}" style="color: #0066cc;">{AGILDTE_WEB_URL}</a>
</div>
'''


def _tiene_credenciales_ses_api() -> bool:
    """True si hay credenciales IAM para usar SES vía API (HTTPS, puerto 443)."""
    key = os.environ.get('AWS_ACCESS_KEY_ID', '').strip()
    secret = os.environ.get('AWS_SECRET_ACCESS_KEY', '').strip()
    return bool(key and secret)


def _obtener_config_smtp(emp) -> dict | None:
    """
    Devuelve la configuración SMTP a usar.
    Prioridad: campos del modelo Empresa → variables de entorno EMAIL_*.
    Retorna None si no hay configuración disponible.
    """
    # 1. Configuración específica de la empresa
    if emp and emp.smtp_host and emp.smtp_user:
        return {
            'host': emp.smtp_host,
            'port': emp.smtp_port or 587,
            'user': emp.smtp_user,
            'password': emp.smtp_password or '',
            'use_tls': emp.smtp_use_tls if emp.smtp_use_tls is not None else True,
            'from_address': emp.smtp_user,  # La empresa usa su propio usuario como remitente
        }

    # 2. Fallback: variables de entorno del .env
    env_host = os.environ.get('EMAIL_HOST', '').strip()
    env_user = os.environ.get('EMAIL_HOST_USER', '').strip()
    if env_host and env_user:
        # EMAIL_FROM_ADDRESS permite un "nombre visible" (ej: "AgilDTE <facturas@agildte.com>").
        # Si no está definido, se usa el usuario SMTP directamente.
        from_address = os.environ.get('EMAIL_FROM_ADDRESS', '').strip() or env_user
        return {
            'host': env_host,
            'port': int(os.environ.get('EMAIL_PORT', '587')),
            'user': env_user,
            'password': os.environ.get('EMAIL_HOST_PASSWORD', ''),
            'use_tls': os.environ.get('EMAIL_USE_TLS', 'true').lower() in ('1', 'true', 'yes'),
            'from_address': from_address,
        }

    return None


def _obtener_destinatario(venta) -> str:
    """Obtiene el correo del destinatario (cliente o venta)."""
    if venta.cliente and venta.cliente.email_contacto:
        return venta.cliente.email_contacto.strip()
    correo = getattr(venta, 'correo_receptor', None)
    if correo:
        return str(correo).strip()
    return ""


def _aplicar_template(template: str, venta) -> str:
    """Sustituye variables en la plantilla."""
    if not template:
        return ""
    cliente_nombre = (
        venta.nombre_receptor or
        (venta.cliente.nombre if venta.cliente else "") or
        "Cliente"
    )
    numero = venta.numero_control or venta.codigo_generacion or venta.numero_documento or ""
    fecha = venta.fecha_emision.strftime("%d/%m/%Y") if venta.fecha_emision else ""
    total = 0
    if venta.venta_gravada is not None:
        total += float(venta.venta_gravada)
    if venta.debito_fiscal is not None:
        total += float(venta.debito_fiscal)
    total_str = f"${total:,.2f}" if total else ""

    return (
        template
        .replace("{{cliente}}", cliente_nombre)
        .replace("{{numero_control}}", numero)
        .replace("{{fecha}}", fecha)
        .replace("{{total}}", total_str)
    )


def enviar_factura_email(venta) -> bool:
    """
    Envía el correo con la factura (PDF + JSON) al cliente.
    Solo se envía si el DTE fue aceptado por MH (estado_dte == 'AceptadoMH').
    Usa la configuración SMTP de la empresa o las variables de entorno EMAIL_* como fallback.
    Los errores de red se registran en el log pero NO bloquean el flujo principal.
    Retorna True si se envió correctamente, False en cualquier otro caso.
    """
    if not venta.empresa:
        logger.warning("Venta sin empresa, no se puede enviar correo")
        return False

    # Solo enviar si el DTE fue aceptado por MH
    estado = getattr(venta, 'estado_dte', None)
    if estado != 'AceptadoMH':
        logger.info(f"Venta {venta.id} con estado '{estado}' (no AceptadoMH), omitiendo envío de correo")
        return False

    emp = venta.empresa
    smtp_cfg = _obtener_config_smtp(emp)
    from_address = None
    if smtp_cfg:
        from_address = smtp_cfg.get('from_address') or smtp_cfg.get('user')
    if not from_address:
        from_address = os.environ.get('EMAIL_FROM_ADDRESS', '').strip() or os.environ.get('EMAIL_HOST_USER', '').strip()
    use_ses_api = _tiene_credenciales_ses_api()
    if not smtp_cfg and not (use_ses_api and from_address):
        logger.info(
            f"Empresa '{emp.nombre}' sin SMTP configurado y sin credenciales SES API (AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY). "
            f"Omitiendo envío de correo para venta {venta.id}."
        )
        return False

    destinatario = _obtener_destinatario(venta)
    if not destinatario or "@" not in destinatario:
        logger.info(f"Venta {venta.id} sin correo de destinatario, omitiendo envío")
        return False

    # Generar PDF
    try:
        pdf_buffer = generar_pdf_venta(venta)
        pdf_bytes = pdf_buffer.getvalue() if hasattr(pdf_buffer, 'getvalue') else pdf_buffer.read()
    except Exception as e:
        logger.error(f"Error generando PDF para venta {venta.id}: {e}")
        return False

    # Generar JSON DTE (adjunto opcional; si falla no cancela el envío)
    json_bytes = None
    try:
        # Preferir el JWS firmado ya aceptado si está disponible
        if getattr(venta, 'dte_firmado', None):
            json_bytes = venta.dte_firmado.encode('utf-8') if isinstance(venta.dte_firmado, str) else venta.dte_firmado
        else:
            gen = DTEGenerator(venta)
            ambiente = emp.ambiente or '01'
            dte_json = gen.generar_json(ambiente=ambiente)
            json_bytes = json.dumps(dte_json, indent=2, ensure_ascii=False).encode('utf-8')
    except Exception as e:
        logger.warning(f"No se pudo generar JSON DTE para adjuntar en correo de venta {venta.id}: {e}")

    # Cuerpo del mensaje
    template = emp.email_template_html or (
        '<p>Estimado(a) {{cliente}},</p>'
        '<p>Adjuntamos su factura electrónica {{numero_control}}.</p>'
        '<p>Saludos cordiales.</p>'
    )
    cuerpo_html = _aplicar_template(template, venta) + BRANDING_HTML

    asunto_template = emp.email_asunto_default or "Factura electrónica - {{numero_control}}"
    asunto = _aplicar_template(asunto_template, venta)

    msg = MIMEMultipart('alternative')
    msg['Subject'] = asunto
    msg['From'] = from_address
    msg['To'] = destinatario

    msg.attach(MIMEText(cuerpo_html, 'html', 'utf-8'))

    # Adjuntar PDF
    adj_pdf = MIMEBase('application', 'pdf')
    adj_pdf.set_payload(pdf_bytes)
    encoders.encode_base64(adj_pdf)
    nombre_pdf = f"Factura_{venta.numero_control or venta.id}.pdf".replace("/", "-")
    adj_pdf.add_header('Content-Disposition', 'attachment', filename=nombre_pdf)
    msg.attach(adj_pdf)

    # Adjuntar JSON (DTE firmado)
    if json_bytes:
        adj_json = MIMEBase('application', 'json')
        adj_json.set_payload(json_bytes)
        encoders.encode_base64(adj_json)
        nombre_json = f"DTE_{venta.codigo_generacion or venta.id}.json".replace("/", "-")
        adj_json.add_header('Content-Disposition', 'attachment', filename=nombre_json)
        msg.attach(adj_json)

    # Enviar — prioridad: SES API (HTTPS 443) si hay credenciales IAM; sino SMTP
    raw_bytes = msg.as_bytes() if hasattr(msg, 'as_bytes') else msg.as_string().encode('utf-8')

    if use_ses_api:
        try:
            _enviar_via_ses_api(raw_bytes, from_address, destinatario)
            logger.info(f"Correo enviado vía SES API a {destinatario} para venta {venta.id} (DTE {venta.codigo_generacion})")
            return True
        except Exception as e:
            logger.error(
                f"Error SES API enviando correo para venta {venta.id} a {destinatario}: {e}. "
                f"La factura fue procesada correctamente por MH."
            )
            return False

    if not smtp_cfg:
        logger.warning("Credenciales SES API no disponibles y SMTP no configurado, no se envió correo")
        return False

    try:
        if smtp_cfg['use_tls']:
            server = smtplib.SMTP(smtp_cfg['host'], smtp_cfg['port'], timeout=30)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            server = smtplib.SMTP_SSL(smtp_cfg['host'], smtp_cfg['port'], timeout=30)

        if smtp_cfg['password']:
            server.login(smtp_cfg['user'], smtp_cfg['password'])
        from_raw = smtp_cfg.get('from_address') or smtp_cfg['user']
        m = re.search(r'<([^>]+)>', from_raw)
        mail_from = m.group(1) if m else from_raw
        server.sendmail(mail_from, [destinatario], msg.as_string())
        server.quit()
        logger.info(f"Correo enviado vía SMTP a {destinatario} para venta {venta.id} (DTE {venta.codigo_generacion})")
        return True
    except (smtplib.SMTPException, OSError, TimeoutError) as e:
        logger.error(
            f"Error de red/SMTP enviando correo para venta {venta.id} a {destinatario}: {e}. "
            f"La factura fue procesada correctamente por MH."
        )
        return False
    except Exception as e:
        logger.error(f"Error inesperado enviando correo para venta {venta.id}: {e}")
        return False


def _enviar_via_ses_api(raw_message_bytes: bytes, source: str, destination: str) -> None:
    """
    Envía correo vía Amazon SES API (HTTPS, puerto 443).
    Requiere AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY y opcionalmente AWS_REGION.
    """
    import boto3

    region = os.environ.get('AWS_REGION', '').strip() or os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
    client = boto3.client('ses', region_name=region)
    client.send_raw_email(
        Source=source,
        Destinations=[destination],
        RawMessage={'Data': raw_message_bytes},
    )
