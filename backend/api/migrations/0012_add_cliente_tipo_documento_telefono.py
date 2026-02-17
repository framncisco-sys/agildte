# Generated manually for Gestión de Clientes (MH)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_add_error_envio_venta'),
    ]

    operations = [
        migrations.AddField(
            model_name='cliente',
            name='tipo_documento',
            field=models.CharField(
                blank=True,
                choices=[('NIT', 'NIT'), ('DUI', 'DUI'), ('Pasaporte', 'Pasaporte')],
                help_text='Tipo de documento de identidad según MH',
                max_length=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='cliente',
            name='documento_identidad',
            field=models.CharField(
                blank=True,
                help_text='NIT, DUI o Pasaporte según tipo_documento',
                max_length=30,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='cliente',
            name='telefono',
            field=models.CharField(
                blank=True,
                help_text='Teléfono de contacto (opcional)',
                max_length=20,
                null=True,
            ),
        ),
    ]
