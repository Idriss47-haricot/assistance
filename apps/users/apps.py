# apps/users/apps.py - VERSION CORRIGÉE
from django.apps import AppConfig

class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'
    
    def ready(self):
        # Commenté pour éviter l'erreur
        # import apps.users.signals  # noqa
        pass