from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
import ldap
import os

User = get_user_model()


class LDAPBackend(ModelBackend):
    """
    Backend d'authentification LDAP (simulé)
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Si c'est un développement, simuler le LDAP
        if os.getenv('DEBUG', 'True') == 'True':
            return self._simulate_ldap_auth(username, password)
        else:
            return self._real_ldap_auth(username, password)
    
    def _simulate_ldap_auth(self, username, password):
        """
        Simulation LDAP pour développement
        """
        try:
            # Vérifier que l'utilisateur existe
            user = User.objects.get(username=username)
            
            # En développement, accepter le mot de passe normal
            if user.check_password(password):
                return user
            
            # Simuler LDAP : si utilisateur existe, authentifier
            # Dans un cas réel, on vérifierait les credentials LDAP
            return None
            
        except User.DoesNotExist:
            return None
    
    def _real_ldap_auth(self, username, password):
        """
        Authentification LDAP réelle
        """
        try:
            # Connexion au serveur LDAP
            ldap_server = os.getenv('LDAP_SERVER', 'ldap://localhost:389')
            base_dn = os.getenv('LDAP_BASE_DN', 'dc=company,dc=com')
            
            conn = ldap.initialize(ldap_server)
            conn.set_option(ldap.OPT_REFERRALS, 0)
            
            # Recherche de l'utilisateur
            search_filter = f"(&(objectClass=person)(uid={username}))"
            result = conn.search_s(base_dn, ldap.SCOPE_SUBTREE, search_filter)
            
            if not result:
                return None
            
            user_dn = result[0][0]
            
            # Tentative de bind avec les credentials
            try:
                conn.simple_bind_s(user_dn, password)
                # Authentification réussie
                
                # Créer ou mettre à jour l'utilisateur dans Django
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': f"{username}@company.com",
                        'first_name': username,
                        'last_name': username,
                        'ldap_uid': user_dn,
                    }
                )
                
                if created:
                    user.set_unusable_password()
                    user.save()
                
                return user
                
            except ldap.INVALID_CREDENTIALS:
                return None
                
        except Exception as e:
            # Log l'erreur
            print(f"LDAP Error: {e}")
            return None