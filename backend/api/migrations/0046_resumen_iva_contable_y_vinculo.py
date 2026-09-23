# Generada para entorno LOCAL. No aplicar en el VPS productivo hasta validar.
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0045_registro_auditoria'),
    ]

    operations = [
        migrations.AddField(
            model_name='empresa',
            name='sistema_contable_empresa_id',
            field=models.UUIDField(
                blank=True,
                help_text='UUID de EmpresaCliente en el sistema contable (vínculo explícito).',
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name='empresa',
            name='sync_contable_habilitado',
            field=models.BooleanField(
                default=False,
                help_text='Si está activo, acepta publicación de resumen IVA desde el sistema contable.',
            ),
        ),
        migrations.CreateModel(
            name='ResumenIvaMensualContable',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('periodo', models.CharField(help_text='YYYY-MM', max_length=7)),
                ('ventas', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('debito', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('retencion', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('compras', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('credito_fiscal', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('valor_a_pagar', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('generado_en', models.DateTimeField(blank=True, null=True)),
                ('origen', models.CharField(default='sistema_contable', max_length=40)),
                ('checksum', models.CharField(blank=True, default='', max_length=64)),
                ('nrc_reportado', models.CharField(blank=True, default='', max_length=20)),
                ('documento_reportado', models.CharField(
                    blank=True,
                    default='',
                    help_text='NIT o DUI normalizado enviado por el contable.',
                    max_length=30,
                )),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('empresa', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='resumenes_iva_contable',
                    to='api.empresa',
                )),
            ],
            options={
                'verbose_name': 'Resumen IVA mensual (contable)',
                'verbose_name_plural': 'Resúmenes IVA mensuales (contable)',
                'ordering': ['-periodo', 'empresa_id'],
            },
        ),
        migrations.AddConstraint(
            model_name='resumenivamensualcontable',
            constraint=models.UniqueConstraint(
                fields=('empresa', 'periodo'),
                name='uniq_resumen_iva_contable_empresa_periodo',
            ),
        ),
    ]
