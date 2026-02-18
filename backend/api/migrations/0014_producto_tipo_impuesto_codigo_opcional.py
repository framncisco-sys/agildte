# Generated - Producto: tipo_impuesto, codigo opcional, UniqueConstraint por empresa+codigo

from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0013_actividadeconomica'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='tipo_impuesto',
            field=models.CharField(
                choices=[('20', 'Gravado 13% (IVA)'), ('exento', 'Exento')],
                default='20',
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name='producto',
            name='codigo',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
        migrations.AlterUniqueTogether(
            name='producto',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='producto',
            constraint=models.UniqueConstraint(
                condition=~Q(codigo=''),
                fields=('empresa', 'codigo'),
                name='producto_empresa_codigo_uniq',
            ),
        ),
    ]
