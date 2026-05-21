# Generated manually — WhatsApp Cloud API (Meta) por empresa
from django.db import migrations, models

import api.utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0034_rename_groups_posagil_agildte'),
    ]

    operations = [
        migrations.AddField(
            model_name='empresa',
            name='whatsapp_premium_enabled',
            field=models.BooleanField(
                default=False,
                help_text='Si está activo, la empresa puede enviar facturas por WhatsApp Cloud API (Meta).',
            ),
        ),
        migrations.AddField(
            model_name='empresa',
            name='whatsapp_phone_number_id',
            field=models.CharField(
                blank=True,
                help_text='ID del número de teléfono en Meta Business (WhatsApp Cloud API).',
                max_length=32,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='empresa',
            name='whatsapp_access_token',
            field=api.utils.fields.EncryptedCharField(
                blank=True,
                help_text='Token de acceso permanente de la app Meta (cifrado en BD).',
                max_length=2000,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='empresa',
            name='whatsapp_business_account_id',
            field=models.CharField(
                blank=True,
                help_text='Opcional: WABA ID en Meta (referencia administrativa).',
                max_length=64,
                null=True,
            ),
        ),
    ]
