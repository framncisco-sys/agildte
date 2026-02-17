# Generated for fecha_hora_emision support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0009_add_observaciones_mh'),
    ]

    operations = [
        migrations.AddField(
            model_name='venta',
            name='hora_emision',
            field=models.CharField(blank=True, help_text='Hora real del DTE (HH:MM:SS) según MH', max_length=10, null=True),
        ),
    ]
