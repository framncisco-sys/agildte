# Generated for MH V2 — snapshot ubicación receptor en venta

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0042_empresa_cliente_distrito'),
    ]

    operations = [
        migrations.AddField(
            model_name='venta',
            name='departamento_receptor',
            field=models.CharField(
                blank=True,
                help_text='CAT-012 departamento del receptor (snapshot MH V2)',
                max_length=2,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='venta',
            name='municipio_receptor',
            field=models.CharField(
                blank=True,
                help_text='CAT-013 municipio nuevo del receptor (snapshot MH V2)',
                max_length=2,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='venta',
            name='distrito_receptor',
            field=models.CharField(
                blank=True,
                help_text='CAT-008 distrito del receptor (snapshot MH V2)',
                max_length=2,
                null=True,
            ),
        ),
    ]
