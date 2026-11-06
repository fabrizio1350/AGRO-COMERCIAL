from django.db import migrations, models
import django.core.validators
import mercado.models


class Migration(migrations.Migration):
    """La verificacion deja de pedir chacra y padron agrario: ahora comprueba que la persona atiende un puesto."""

    dependencies = [
        ('mercado', '0014_puestos_de_mercado'),
    ]

    operations = [
        migrations.RenameField('verificacionvendedor', 'foto_chacra', 'foto_en_puesto'),
        migrations.RenameField('verificacionvendedor', 'inscrito_padron', 'declara_puesto'),
        migrations.RenameField('verificacionvendedor', 'revisado_chacra', 'revisado_puesto'),
        migrations.RenameField('verificacionvendedor', 'revisado_padron', 'revisado_constancia'),
        migrations.AddField(
            model_name='verificacionvendedor',
            name='constancia_puesto',
            field=models.FileField(blank=True, help_text='Carnet o recibo de la asociación del mercado, recibo de merced conductiva o licencia municipal', storage=mercado.models.AlmacenVerificaciones(), upload_to='verificaciones/', validators=[django.core.validators.FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp', 'pdf'])]),
        ),
        migrations.AlterField(
            model_name="pagocomision",
            name="metodo_pago",
            field=models.CharField(
                choices=[
                    ("YAPE_PLIN", "Yape / Plin"),
                    ("TARJETA", "Tarjeta de crédito o débito"),
                ],
                default="YAPE_PLIN",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="verificacionvendedor",
            name="declara_puesto",
            field=models.BooleanField(
                default=False, verbose_name="Declara que atiende el puesto"
            ),
        ),
        migrations.AlterField(
            model_name="verificacionvendedor",
            name="distrito",
            field=models.CharField(max_length=120, verbose_name="Mercado declarado"),
        ),
        migrations.AlterField(
            model_name="verificacionvendedor",
            name="nombre_organizacion",
            field=models.CharField(
                blank=True, max_length=150, verbose_name="Nombre comercial"
            ),
        ),
        migrations.AlterField(
            model_name="verificacionvendedor",
            name="revisado_constancia",
            field=models.BooleanField(
                default=False,
                help_text="El carnet, recibo o licencia es del mismo mercado y puesto",
                verbose_name="Constancia del puesto válida",
            ),
        ),
        migrations.AlterField(
            model_name="verificacionvendedor",
            name="revisado_identidad",
            field=models.BooleanField(
                default=False,
                help_text="El DNI coincide con la persona de la foto",
                verbose_name="Identidad comprobada",
            ),
        ),
        migrations.AlterField(
            model_name="verificacionvendedor",
            name="revisado_organizacion",
            field=models.BooleanField(
                default=False,
                help_text="RUC activo en SUNAT",
                verbose_name="RUC comprobado",
            ),
        ),
        migrations.AlterField(
            model_name="verificacionvendedor",
            name="revisado_puesto",
            field=models.BooleanField(
                default=False,
                help_text="Se ve a la persona en su puesto y coincide con el mercado y número marcados en el mapa",
                verbose_name="Foto en el puesto válida",
            ),
        ),
        migrations.AlterField(
            model_name="verificacionvendedor",
            name="tipo",
            field=models.CharField(
                choices=[
                    ("PERSONA", "Persona natural"),
                    ("ORGANIZACION", "Negocio con RUC"),
                ],
                default="PERSONA",
                max_length=15,
            ),
        ),
    ]
