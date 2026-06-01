from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0039_alter_perfilusuario_and_venta_doc_relacionado'),
    ]

    operations = [
        migrations.AddField(
            model_name='empresa',
            name='dashboard_compras_premium_enabled',
            field=models.BooleanField(
                default=False,
                help_text='Si está activo, el dashboard AgilDTE muestra el cuadro «Compras del mes» (IVA débito/crédito).',
            ),
        ),
    ]
