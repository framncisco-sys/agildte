from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0044_venta_nombre_comercial_receptor"),
    ]

    operations = [
        migrations.CreateModel(
            name="RegistroAuditoria",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("creado_en", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("evento", models.CharField(db_index=True, max_length=40)),
                ("username", models.CharField(blank=True, db_index=True, default="", max_length=150)),
                ("ip_address", models.CharField(blank=True, db_index=True, default="", max_length=45)),
                ("user_agent", models.CharField(blank=True, default="", max_length=500)),
                ("detalle", models.TextField(blank=True, default="")),
                ("venta_id", models.IntegerField(blank=True, db_index=True, null=True)),
                ("empresa_id", models.IntegerField(blank=True, null=True)),
            ],
            options={
                "verbose_name": "Registro de auditoría",
                "verbose_name_plural": "Registros de auditoría",
                "ordering": ["-creado_en"],
            },
        ),
    ]
