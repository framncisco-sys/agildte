# Generated migration to update email templates to new format

from django.db import migrations


ASUNTO_VIEJO = "Factura electrónica - {{numero_control}}"
ASUNTO_NUEVO = "Factura electrónica de {{nombre_empresa}} - {{codigo_generacion}}"

CUERPO_VIEJO = (
    "<p>Estimado(a) {{cliente}},</p>"
    "<p>Adjuntamos su factura electrónica {{numero_control}}.</p>"
    "<p>Saludos cordiales.</p>"
)
CUERPO_NUEVO = (
    "<p>Estimado(a) {{cliente}},</p>"
    "<p>Adjuntamos su factura electrónica (\"{{codigo_generacion}}\") por parte de {{nombre_empresa}}.</p>"
    "<p>Puede descargar el documento PDF y el archivo JSON correspondientes que se encuentran adjuntos en este correo para sus registros.</p>"
    "<p>Saludos cordiales.</p>"
)


def actualizar_plantillas(apps, schema_editor):
    Empresa = apps.get_model("api", "Empresa")
    for emp in Empresa.objects.all():
        actualizar = False
        if emp.email_asunto_default == ASUNTO_VIEJO or (emp.email_asunto_default or "").strip() == "":
            emp.email_asunto_default = ASUNTO_NUEVO
            actualizar = True
        if (
            (emp.email_template_html or "").strip() == ""
            or emp.email_template_html == CUERPO_VIEJO
        ):
            emp.email_template_html = CUERPO_NUEVO
            actualizar = True
        if actualizar:
            emp.save()


def revertir(apps, schema_editor):
    Empresa = apps.get_model("api", "Empresa")
    for emp in Empresa.objects.all():
        actualizar = False
        if emp.email_asunto_default == ASUNTO_NUEVO:
            emp.email_asunto_default = ASUNTO_VIEJO
            actualizar = True
        if emp.email_template_html == CUERPO_NUEVO:
            emp.email_template_html = CUERPO_VIEJO
            actualizar = True
        if actualizar:
            emp.save()


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0029_plantillafactura_orden"),
    ]

    operations = [
        migrations.RunPython(actualizar_plantillas, revertir),
    ]
