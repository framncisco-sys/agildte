# Generated manually for add_ambiente_emision_venta

from django.db import migrations, models


def set_ambiente_from_empresa(apps, schema_editor):
    Venta = apps.get_model('api', 'Venta')
    for v in Venta.objects.select_related('empresa').all():
        v.ambiente_emision = v.empresa.ambiente if v.empresa else '01'
        v.save(update_fields=['ambiente_emision'])


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0021_unify_user_roles_remove_rol_from_perfil'),
    ]

    operations = [
        migrations.AddField(
            model_name='venta',
            name='ambiente_emision',
            field=models.CharField(
                choices=[('00', 'PRODUCCION'), ('01', 'PRUEBAS')],
                db_index=True,
                default='01',
                help_text="Ambiente en que se emitió: '00'=Producción, '01'=Pruebas",
                max_length=2,
            ),
        ),
        migrations.RunPython(set_ambiente_from_empresa, migrations.RunPython.noop),
    ]
