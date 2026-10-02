from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0046_resumen_iva_contable_y_vinculo'),
    ]

    operations = [
        migrations.AddField(
            model_name='venta',
            name='fecha_anulacion',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='Momento en que MH procesó el evento de invalidación (null en anulados históricos)',
            ),
        ),
        migrations.AddField(
            model_name='venta',
            name='codigo_generacion_anulacion',
            field=models.CharField(
                blank=True,
                max_length=36,
                null=True,
                help_text='codigoGeneracion del evento de invalidación enviado a MH',
            ),
        ),
        migrations.AddField(
            model_name='venta',
            name='sello_anulacion',
            field=models.CharField(
                blank=True,
                max_length=100,
                null=True,
                help_text='selloRecibido devuelto por MH para el evento de invalidación',
            ),
        ),
    ]
