# Generated manually - Venta.cliente ahora opcional (Consumidor Final)

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_cliente_cod_actividad_cliente_desc_actividad'),
    ]

    operations = [
        migrations.AlterField(
            model_name='venta',
            name='cliente',
            field=models.ForeignKey(
                blank=True,
                help_text='Opcional: Consumidor Final puede ser null; usar nombre_receptor/nrc_receptor',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='compras_hechas',
                to='api.cliente'
            ),
        ),
    ]
