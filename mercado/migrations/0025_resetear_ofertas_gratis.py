from django.db import migrations, models


def dar_tres_gratis_a_todas(apps, schema_editor):
    """Todas las cuentas que ya existen empiezan con sus 3 publicaciones de oferta gratis."""
    PerfilUsuario = apps.get_model('mercado', 'PerfilUsuario')
    PerfilUsuario.objects.update(ofertas_premium_regalo=3)


class Migration(migrations.Migration):

    dependencies = [
        ('mercado', '0024_ofertas_premium_regalo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='perfilusuario',
            name='ofertas_premium_regalo',
            field=models.PositiveSmallIntegerField(
                default=3, help_text='Cada cuenta empieza con 3. Se descuenta una cada vez que publica una oferta con "Publicar gratis".',
                verbose_name='Publicaciones de oferta gratis que le quedan'),
        ),
        migrations.RunPython(dar_tres_gratis_a_todas, migrations.RunPython.noop),
    ]
