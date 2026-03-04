# Precio unitario 8 decimales para cálculos internos (medida/unidad).
# MH sigue recibiendo 2 decimales en el JSON (ya aplicado en builders).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0027_precio_unitario_5_decimales'),
    ]

    operations = [
        migrations.AlterField(
            model_name='producto',
            name='precio_unitario',
            field=models.DecimalField(decimal_places=8, default=0.00, max_digits=14),
        ),
        migrations.AlterField(
            model_name='detalleventa',
            name='precio_unitario',
            field=models.DecimalField(decimal_places=8, default=0.00, max_digits=14),
        ),
        migrations.AlterField(
            model_name='plantillaitem',
            name='precio_unitario',
            field=models.DecimalField(decimal_places=8, default=0.00, max_digits=14),
        ),
    ]
