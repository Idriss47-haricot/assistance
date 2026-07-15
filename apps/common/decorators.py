from django.core.cache import cache
from functools import wraps
import hashlib
import json
from django.conf import settings

def cache_view(timeout=None, key_prefix=None):
    """
    Décorateur pour mettre en cache les vues
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Ne pas cacher si DEBUG est activé
            if settings.DEBUG:
                return view_func(request, *args, **kwargs)
            
            # Générer une clé de cache unique
            cache_key = generate_cache_key(request, view_func, key_prefix)
            
            # Vérifier le cache
            response = cache.get(cache_key)
            if response is not None:
                return response
            
            # Générer la réponse
            response = view_func(request, *args, **kwargs)
            
            # Mettre en cache
            cache_timeout = timeout or settings.CACHE_MIDDLEWARE_SECONDS
            cache.set(cache_key, response, cache_timeout)
            
            return response
        return wrapper
    return decorator


def generate_cache_key(request, view_func, key_prefix=None):
    """
    Génère une clé de cache unique basée sur la requête
    """
    # Informations de base
    view_name = f"{view_func.__module__}.{view_func.__name__}"
    path = request.path
    method = request.method
    
    # Paramètres GET
    query_params = sorted(request.GET.items())
    
    # Utilisateur
    user_id = request.user.id if request.user.is_authenticated else 'anonymous'
    
    # Clé
    key_data = {
        'view': view_name,
        'path': path,
        'method': method,
        'params': query_params,
        'user': user_id,
    }
    
    key_str = json.dumps(key_data, sort_keys=True)
    key_hash = hashlib.md5(key_str.encode()).hexdigest()
    
    prefix = key_prefix or 'view_cache'
    return f"{prefix}:{key_hash}"


def invalidate_cache(pattern):
    """
    Invalide le cache selon un pattern.
    Si django_redis n'est pas installé/configuré (ex: en dev local),
    on ignore silencieusement au lieu de faire planter la requête.
    """
    try:
        from django_redis import get_redis_connection
    except ModuleNotFoundError:
        return

    try:
        conn = get_redis_connection("default")
        keys = conn.keys(f"*{pattern}*")
        if keys:
            conn.delete(*keys)
    except Exception:
        # Redis non disponible (pas démarré, mauvaise config, etc.)
        # On n'interrompt jamais la logique métier pour un problème de cache.
        pass