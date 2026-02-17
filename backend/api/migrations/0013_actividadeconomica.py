# Generated manually - Catálogo Actividad Económica (MH)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0012_add_cliente_tipo_documento_telefono'),
    ]

    operations = [
        migrations.CreateModel(
            name='ActividadEconomica',
            fields=[
                ('codigo', models.CharField(max_length=10, primary_key=True, serialize=False)),
                ('descripcion', models.CharField(max_length=255)),
            ],
            options={
                'verbose_name': 'Actividad Económica',
                'verbose_name_plural': 'Actividades Económicas',
                'ordering': ['codigo'],
            },
        ),
    ]
