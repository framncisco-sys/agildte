"""
Servicio de envío de correos con facturas (PDF + JSON/XML).
Incluye branding AgilDTE en el pie de cada correo.
"""
import json
import logging
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
    Usa la configuración SMTP de la empresa.
    Retorna True si se envió correctamente.
    """
    if not venta.empresa:
        logger.warning("Venta sin empresa, no se puede enviar correo")
        return False

    emp = venta.empresa
    if not emp.smtp_host or not emp.smtp_user:
        logger.info(f"Empresa {emp.nombre} sin SMTP configurado, omitiendo envío de correo")
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

    # Generar JSON DTE
    try:
        gen = DTEGenerator(venta)
        ambiente = emp.ambiente or '01'
        dte_json = gen.generar_json(ambiente=ambiente)
        json_bytes = json.dumps(dte_json, indent=2, ensure_ascii=False).encode('utf-8')
    except Exception as e:
        logger.error(f"Error generando JSON DTE para venta {venta.id}: {e}")
        json_bytes = None

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
    msg['From'] = emp.smtp_user
    msg['To'] = destinatario

    msg.attach(MIMEText(cuerpo_html, 'html', 'utf-8'))

    # Adjuntar PDF
    adj_pdf = MIMEBase('application', 'pdf')
    adj_pdf.set_payload(pdf_bytes)
    encoders.encode_base64(adj_pdf)
    nombre_pdf = f"Factura_{venta.numero_control or venta.id}.pdf".replace("/", "-")
    adj_pdf.add_header('Content-Disposition', 'attachment', filename=nombre_pdf)
    msg.attach(adj_pdf)

    # Adjuntar JSON (DTE)
    if json_bytes:
        adj_json = MIMEBase('application', 'json')
        adj_json.set_payload(json_bytes)
        encoders.encode_base64(adj_json)
        nombre_json = f"DTE_{venta.codigo_generacion or venta.id}.json".replace("/", "-")
        adj_json.add_header('Content-Disposition', 'attachment', filename=nombre_json)
        msg.attach(adj_json)

    try:
        if emp.smtp_use_tls:
            server = smtplib.SMTP(emp.smtp_host, emp.smtp_port or 587)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(emp.smtp_host, emp.smtp_port or 465)

        pwd = emp.smtp_password or ""
        if pwd:
            server.login(emp.smtp_user, pwd)
        server.sendmail(emp.smtp_user, [destinatario], msg.as_string())
        server.quit()
        logger.info(f"Correo enviado a {destinatario} para venta {venta.id}")
        return True
    except Exception as e:
        logger.error(f"Error enviando correo para venta {venta.id}: {e}")
        return False
