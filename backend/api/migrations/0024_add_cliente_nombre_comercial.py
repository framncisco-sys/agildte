# Generated manually - add nombre_comercial to Cliente for DTE-03 CCF

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0023_plantillafactura_plantillaitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='cliente',
            name='nombre_comercial',
            field=models.CharField(blank=True, help_text='Nombre comercial del cliente (para DTE-03 CCF)', max_length=200, null=True),
        ),
    ]
