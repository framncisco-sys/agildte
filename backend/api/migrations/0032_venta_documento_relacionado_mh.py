# Generated manually for NC/ND documentoRelacionado persistence (async MH)

from django.db import migrations, models


def _backfill_documento_relacionado(apps, schema_editor):
    Venta = apps.get_model('api', 'Venta')
    tmap = {'CF': '01', 'CCF': '03', 'NC': '05', 'ND': '06', 'FSE': '14'}
    qs = (
        Venta.objects.filter(codigo_generacion_referenciado__isnull=False)
        .exclude(codigo_generacion_referenciado='')
        .filter(documento_relacionado_tipo__isnull=True)
    )
    for v in qs.iterator(chunk_size=200):
        ref = (v.codigo_generacion_referenciado or '').strip()
        if not ref:
            continue
        orig = Venta.objects.filter(codigo_generacion__iexact=ref).first()
        if orig:
            v.documento_relacionado_tipo = tmap.get(orig.tipo_venta, '03')
            v.documento_relacionado_tipo_generacion = 2
            v.documento_relacionado_numero_control = orig.numero_control
            v.documento_relacionado_fecha_emision = orig.fecha_emision
        else:
            v.documento_relacionado_tipo = '03'
            v.documento_relacionado_tipo_generacion = 2
            v.documento_relacionado_fecha_emision = v.fecha_emision
        v.save(
            update_fields=[
                'documento_relacionado_tipo',
                'documento_relacionado_tipo_generacion',
                'documento_relacionado_numero_control',
                'documento_relacionado_fecha_emision',
            ]
        )


def _noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0031_alter_plantillafactura_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='venta',
            name='documento_relacionado_tipo',
            field=models.CharField(
                blank=True, help_text='MH documentoRelacionado.tipoDocumento: 01=CF, 03=CCF, 05=NC, 06=ND, 14=FSE',
                max_length=2, null=True,
            ),
        ),
        migrations.AddField(
            model_name='venta',
            name='documento_relacionado_tipo_generacion',
            field=models.IntegerField(
                blank=True, default=2,
                help_text='MH tipoGeneracion del doc. relacionado (2 = código de generación / UUID)',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='venta',
            name='documento_relacionado_numero_control',
            field=models.CharField(
                blank=True, help_text='numeroControl del DTE relacionado si aplica (31 caracteres)',
                max_length=100, null=True,
            ),
        ),
        migrations.AddField(
            model_name='venta',
            name='documento_relacionado_fecha_emision',
            field=models.DateField(
                blank=True, help_text='fechaEmision del DTE relacionado para NC/ND', null=True,
            ),
        ),
        migrations.RunPython(_backfill_documento_relacionado, _noop_reverse),
    ]
