# Generated manually for Historial de Documentos

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0008_add_receptor_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='venta',
            name='observaciones_mh',
            field=models.TextField(blank=True, help_text='Errores/observaciones de MH al rechazar', null=True),
        ),
    ]
