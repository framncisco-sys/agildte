# Ampliar descripción de línea DTE (catálogo, detalle venta, plantillas) a 1000 caracteres (esquema MH).

from django.db import migrations, models

from api.constants import DTE_LINEA_DESCRIPCION_MAX_LENGTH


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0036_tareafacturacion_whatsapp'),
    ]

    operations = [
        migrations.AlterField(
            model_name='detalleventa',
            name='descripcion_libre',
            field=models.CharField(blank=True, max_length=DTE_LINEA_DESCRIPCION_MAX_LENGTH, null=True),
        ),
        migrations.AlterField(
            model_name='plantillaitem',
            name='descripcion_libre',
            field=models.CharField(blank=True, max_length=DTE_LINEA_DESCRIPCION_MAX_LENGTH, null=True),
        ),
        migrations.AlterField(
            model_name='producto',
            name='descripcion',
            field=models.CharField(max_length=DTE_LINEA_DESCRIPCION_MAX_LENGTH),
        ),
    ]
