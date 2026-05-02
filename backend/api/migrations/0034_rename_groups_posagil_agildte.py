# Renombra grupos de auth a nombres estandarizados (permissions.GRUPO_*).

from django.db import migrations


def rename_groups_forward(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    # (nombre_antiguo, nombre_nuevo)
    renames = [
        ("Administrador", "AgilDTE - Administrador"),
        ("Contador", "AgilDTE - Contador"),
        ("Vendedor", "AgilDTE - Vendedor"),
        ("PosAgil Vendedor", "PosAgil - Vendedor"),
    ]
    for old, new in renames:
        g = Group.objects.filter(name=old).first()
        if g and not Group.objects.filter(name=new).exists():
            g.name = new
            g.save(update_fields=["name"])
        elif not Group.objects.filter(name=new).exists():
            Group.objects.get_or_create(name=new)

    # Grupo para admins de PosAgil en portal AgilDTE (asignación manual en admin)
    Group.objects.get_or_create(name="PosAgil - Administrador")


def rename_groups_backward(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    reverse = [
        ("AgilDTE - Administrador", "Administrador"),
        ("AgilDTE - Contador", "Contador"),
        ("AgilDTE - Vendedor", "Vendedor"),
        ("PosAgil - Vendedor", "PosAgil Vendedor"),
    ]
    for new, old in reverse:
        g = Group.objects.filter(name=new).first()
        if g and not Group.objects.filter(name=old).exists():
            g.name = old
            g.save(update_fields=["name"])
    Group.objects.filter(name="PosAgil - Administrador").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0033_perfil_posagil_grupo_pos_vendedor"),
    ]

    operations = [
        migrations.RunPython(rename_groups_forward, rename_groups_backward),
    ]
