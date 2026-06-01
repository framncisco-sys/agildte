from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0037_descripcion_linea_dte_1000'),
    ]

    operations = [
        migrations.AddField(
            model_name='empresa',
            name='tipo_sistema',
            field=models.CharField(
                choices=[
                    ('AGILDTE', 'AgilDTE (facturación nativa SaaS)'),
                    ('POSAGIL', 'PosAgil (punto de venta)'),
                    ('MIXTO', 'PosAgil + AgilDTE'),
                ],
                default='AGILDTE',
                help_text='Plataforma principal de facturación operativa de la empresa.',
                max_length=20,
            ),
        ),
    ]
