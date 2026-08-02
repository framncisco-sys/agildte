from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0043_venta_ubicacion_receptor'),
    ]

    operations = [
        migrations.AddField(
            model_name='venta',
            name='nombre_comercial_receptor',
            field=models.CharField(
                blank=True,
                help_text='Nombre comercial del receptor (snapshot al emitir)',
                max_length=200,
                null=True,
            ),
        ),
    ]
