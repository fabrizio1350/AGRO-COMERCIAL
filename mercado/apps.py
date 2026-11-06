from django.apps import AppConfig


class MercadoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mercado'
    verbose_name = 'Mercado Agricola'

    def ready(self):
        from . import seguridad  # noqa: F401  conecta el contador de intentos de login
