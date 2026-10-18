#!/usr/bin/env python
import os
import sys
import django

# Inicializar configuración de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.core.management import call_command

if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    call_command('clean_descartes', dry_run=dry_run)
