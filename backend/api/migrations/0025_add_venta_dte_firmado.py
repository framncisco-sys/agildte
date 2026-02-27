from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0024_add_cliente_nombre_comercial'),
    ]

    operations = [
        migrations.AddField(
            model_name='venta',
            name='dte_firmado',
            field=models.TextField(
                blank=True,
                null=True,
                help_text='JWS firmado del DTE tal como fue enviado y aceptado por MH',
            ),
        ),
    ]
