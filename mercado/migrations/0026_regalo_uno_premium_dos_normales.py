from django.db import migrations, models


def repartir(apps, schema_editor):
    # Pedido del equipo: el regalo pasa a ser 1 oferta premium y 2 normales para todas las cuentas
    apps.get_model('mercado', 'PerfilUsuario').objects.update(ofertas_premium_regalo=1, ofertas_normal_regalo=2)


class Migration(migrations.Migration):

    dependencies = [
        ('mercado', '0025_regalo_premium_para_todas'),
    ]

    operations = [
        migrations.AlterField(
            model_name='perfilusuario',
            name='ofertas_premium_regalo',
            field=models.PositiveSmallIntegerField(default=1, help_text='Regalo de bienvenida: cada cuenta empieza con 1.',
                                                   verbose_name='Ofertas premium gratis que le quedan'),
        ),
        migrations.AddField(
            model_name='perfilusuario',
            name='ofertas_normal_regalo',
            field=models.PositiveSmallIntegerField(default=2, help_text='Regalo de bienvenida: cada cuenta empieza con 2.',
                                                   verbose_name='Ofertas normales gratis que le quedan'),
        ),
        migrations.RunPython(repartir, migrations.RunPython.noop),
    ]
