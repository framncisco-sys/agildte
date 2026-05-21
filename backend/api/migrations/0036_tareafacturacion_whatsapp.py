from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0035_empresa_whatsapp_cloud'),
    ]

    operations = [
        migrations.AddField(
            model_name='tareafacturacion',
            name='enviar_whatsapp_despues',
            field=models.BooleanField(
                default=False,
                help_text='Tras aceptación MH y correo, enviar mensaje WhatsApp al teléfono indicado.',
            ),
        ),
        migrations.AddField(
            model_name='tareafacturacion',
            name='whatsapp_telefono_destino',
            field=models.CharField(blank=True, default='', max_length=32),
        ),
    ]
