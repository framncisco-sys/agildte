# Generated manually — tema de color para PDF comercial

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0040_empresa_dashboard_compras_premium'),
    ]

    operations = [
        migrations.AddField(
            model_name='empresa',
            name='pdf_tema_color',
            field=models.CharField(
                choices=[
                    ('ocean', 'Océano (azul / teal)'),
                    ('emerald', 'Esmeralda (verde)'),
                    ('amber', 'Ámbar (dorado)'),
                ],
                default='ocean',
                help_text='Paleta de color de la factura PDF legible (versión comercial).',
                max_length=20,
            ),
        ),
    ]
