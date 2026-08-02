# Generated for MH V2 schemas — campo distrito (CAT-008)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0041_empresa_pdf_tema_color'),
    ]

    operations = [
        migrations.AddField(
            model_name='empresa',
            name='distrito',
            field=models.CharField(
                blank=True,
                default='14',
                help_text='Código de distrito CAT-008 (2 dígitos). Obligatorio en JSON MH v2/v4.',
                max_length=2,
            ),
        ),
        migrations.AddField(
            model_name='cliente',
            name='distrito',
            field=models.CharField(
                blank=True,
                default='14',
                help_text='Código de distrito CAT-008 (2 dígitos). Obligatorio en JSON MH v2/v4.',
                max_length=2,
            ),
        ),
    ]
