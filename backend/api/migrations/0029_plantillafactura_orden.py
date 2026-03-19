# Campo orden para controlar el orden de visualización de plantillas rápidas.

from django.db import migrations, models


def set_orden_inicial(apps, schema_editor):
    """Asigna orden 1,2,3... según id por empresa."""
    PlantillaFactura = apps.get_model('api', 'PlantillaFactura')
    from django.db.models import Min
    for emp_id in PlantillaFactura.objects.values_list('empresa_id', flat=True).distinct():
        for idx, p in enumerate(PlantillaFactura.objects.filter(empresa_id=emp_id).order_by('id'), start=1):
            p.orden = idx
            p.save(update_fields=['orden'])


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0028_precio_unitario_8_decimales'),
    ]

    operations = [
        migrations.AddField(
            model_name='plantillafactura',
            name='orden',
            field=models.PositiveIntegerField(default=0, help_text='Orden de visualización (1=primero)'),
        ),
        migrations.RunPython(set_orden_inicial, migrations.RunPython.noop),
    ]
