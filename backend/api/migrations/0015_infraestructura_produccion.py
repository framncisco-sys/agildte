# Generated manually - Infraestructura para producción: cifrado, SMTP, TareaFacturacion

from django.db import migrations, models
import django.db.models.deletion
from api.utils.fields import EncryptedCharField


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0014_producto_tipo_impuesto_codigo_opcional'),
    ]

    operations = [
        # 1. Cifrado: clave_api_mh y clave_certificado con EncryptedCharField (max_length 500)
        migrations.AlterField(
            model_name='empresa',
            name='clave_api_mh',
            field=EncryptedCharField(
                blank=True,
                help_text='Contraseña de la API del Ministerio de Hacienda (cifrada en BD)',
                max_length=500,
                null=True
            ),
        ),
        migrations.AlterField(
            model_name='empresa',
            name='clave_certificado',
            field=EncryptedCharField(
                blank=True,
                help_text='Contraseña del archivo de certificado digital (cifrada en BD)',
                max_length=500,
                null=True
            ),
        ),
        # 2. Configuración SMTP y plantilla de correo
        migrations.AddField(
            model_name='empresa',
            name='smtp_host',
            field=models.CharField(blank=True, help_text='Host SMTP (ej: smtp.gmail.com)', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='empresa',
            name='smtp_port',
            field=models.IntegerField(default=587, help_text='Puerto SMTP (587 TLS, 465 SSL)'),
        ),
        migrations.AddField(
            model_name='empresa',
            name='smtp_user',
            field=models.CharField(blank=True, help_text='Usuario SMTP', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='empresa',
            name='smtp_password',
            field=EncryptedCharField(
                blank=True,
                help_text='Contraseña SMTP (cifrada)',
                max_length=500,
                null=True
            ),
        ),
        migrations.AddField(
            model_name='empresa',
            name='smtp_use_tls',
            field=models.BooleanField(default=True, help_text='Usar TLS para conexión SMTP'),
        ),
        migrations.AddField(
            model_name='empresa',
            name='email_asunto_default',
            field=models.CharField(
                blank=True,
                default='Factura electrónica - {{numero_control}}',
                help_text='Asunto del correo. Variables: {{numero_control}}, {{cliente}}, {{fecha}}',
                max_length=255
            ),
        ),
        migrations.AddField(
            model_name='empresa',
            name='email_template_html',
            field=models.TextField(
                blank=True,
                default='<p>Estimado(a) {{cliente}},</p><p>Adjuntamos su factura electrónica {{numero_control}}.</p><p>Saludos cordiales.</p>',
                help_text='Plantilla HTML del cuerpo del correo. Variables: {{cliente}}, {{numero_control}}, {{fecha}}, {{total}}',
                null=True
            ),
        ),
        # 3. Modelo TareaFacturacion (cola de envíos asíncronos)
        migrations.CreateModel(
            name='TareaFacturacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('estado', models.CharField(
                    choices=[('Pendiente', 'Pendiente'), ('Procesando', 'Procesando'), ('Completada', 'Completada'), ('Error', 'Error')],
                    default='Pendiente',
                    max_length=20
                )),
                ('intentos', models.IntegerField(default=0, help_text='Número de intentos de procesamiento')),
                ('proximo_reintento', models.DateTimeField(blank=True, help_text='Cuándo reintentar (exponential backoff)', null=True)),
                ('error_mensaje', models.TextField(blank=True, null=True)),
                ('creada_at', models.DateTimeField(auto_now_add=True)),
                ('actualizada_at', models.DateTimeField(auto_now=True)),
                ('venta', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='tarea_facturacion',
                    to='api.venta'
                )),
            ],
            options={
                'verbose_name': 'Tarea de Facturación',
                'verbose_name_plural': 'Tareas de Facturación',
                'ordering': ['proximo_reintento', 'creada_at'],
            },
        ),
    ]
