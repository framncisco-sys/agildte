# Generated manually for PosAgil integration

from django.db import migrations, models


def crear_grupo_pos_vendedor(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name="PosAgil Vendedor")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0032_venta_documento_relacionado_mh"),
    ]

    operations = [
        migrations.AddField(
            model_name="perfilusuario",
            name="acceso_posagil",
            field=models.BooleanField(
                default=False,
                help_text="Si es verdadero, en AgilDTE se muestra el botón para abrir PosAgil.",
            ),
        ),
        migrations.AddField(
            model_name="perfilusuario",
            name="facturacion_solo_pos",
            field=models.BooleanField(
                default=False,
                help_text="Si es verdadero, se oculta la facturación nativa de AgilDTE (solo PosAgil).",
            ),
        ),
        migrations.RunPython(crear_grupo_pos_vendedor, noop_reverse),
    ]
