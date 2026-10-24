#!/usr/bin/env python
"""Archivo principal de administracion de Django para el proyecto AgroComercial."""
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agro_comercial.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "No se pudo importar Django. Verifica que el entorno virtual este activado."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
