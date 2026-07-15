from django.core.cache import cache
from django.http import JsonResponse
from functools import wraps
import time


def rate_limit(key_prefix, limit=60, period=60):
    """
    Décorateur pour limiter le taux de requêtes
    
    Args:
        key_prefix: Préfixe de la clé de cache
        limit: Nombre max de requêtes
        period: Période en secondes
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Clé unique pour l'utilisateur
            user_id = request.user.id if request.user.is_authenticated else request.META.get('REMOTE_ADDR')
            cache_key = f"rate_limit:{key_prefix}:{user_id}"
            
            # Récupérer les tentatives
            attempts = cache.get(cache_key, [])
            now = time.time()
            
            # Filtrer les tentatives anciennes
            attempts = [t for t in attempts if now - t < period]
            
            if len(attempts) >= limit:
                return JsonResponse({
                    'error': 'Trop de requêtes. Veuillez réessayer plus tard.',
                    'retry_after': int(period - (now - attempts[0]))
                }, status=429)
            
            # Ajouter la nouvelle tentative
            attempts.append(now)
            cache.set(cache_key, attempts, period)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# Utilisation dans les vues API
from apps.common.rate_limit import rate_limit

@rate_limit('api_tickets', limit=100, period=60)
@login_required
def api_ticket_list(request):
    # ... code de l'API ...
    pass