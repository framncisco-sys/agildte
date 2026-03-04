# Generated migration - Precio unitario 5 decimales para cálculos internos.
# MH sigue recibiendo 2 decimales en el JSON (ya aplicado en builders).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0026_seed_actividades_economicas'),
    ]

    operations = [
        migrations.AlterField(
            model_name='producto',
            name='precio_unitario',
            field=models.DecimalField(decimal_places=5, default=0.00, max_digits=12),
        ),
        migrations.AlterField(
            model_name='detalleventa',
            name='precio_unitario',
            field=models.DecimalField(decimal_places=5, default=0.00, max_digits=12),
        ),
        migrations.AlterField(
            model_name='plantillaitem',
            name='precio_unitario',
            field=models.DecimalField(decimal_places=5, default=0.00, max_digits=12),
        ),
    ]
