from django.db import migrations, models


class Migration(migrations.Migration):
    """Las cuentas que ya existian quedan en 0: el regalo es solo para las que se registran desde ahora."""

    dependencies = [
        ('mercado', '0023_nombre_cuentas_ofertas_gratis'),
    ]

    operations = [
        migrations.AddField(
            model_name='perfilusuario',
            name='ofertas_premium_regalo',
            field=models.PositiveSmallIntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='perfilusuario',
            name='ofertas_premium_regalo',
            field=models.PositiveSmallIntegerField(
                default=3, help_text='Regalo de bienvenida: cada cuenta nueva empieza con 3. Se descuenta una por cada oferta nueva.',
                verbose_name='Ofertas premium gratis que le quedan'),
        ),
    ]
