# tpm/apps.py
from django.apps import AppConfig

class TpmConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tpm'

    def ready(self):
        import tpm.signals  # activa los signals al arrancar Django