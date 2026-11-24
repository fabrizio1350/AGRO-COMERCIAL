from django.db import migrations


def dar_tres(apps, schema_editor):
    # Pedido del equipo: todas las cuentas (no solo las nuevas) empiezan con 3 ofertas premium gratis
    apps.get_model('mercado', 'PerfilUsuario').objects.update(ofertas_premium_regalo=3)


class Migration(migrations.Migration):

    dependencies = [
        ('mercado', '0024_ofertas_premium_regalo'),
    ]

    operations = [
        migrations.RunPython(dar_tres, migrations.RunPython.noop),
    ]
