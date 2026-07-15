import time
import logging
from django.utils.deprecation import MiddlewareMixin
from django.db import connection
from django.conf import settings

logger = logging.getLogger('helpdesk.monitoring')


class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """
    Middleware pour monitorer les performances
    """
    
    def process_request(self, request):
        request.start_time = time.time()
        
    def process_response(self, request, response):
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            
            # Log des requêtes lentes (> 1s)
            if duration > 1.0:
                logger.warning(
                    f"Slow request: {request.path} - {duration:.2f}s - "
                    f"User: {request.user.username if request.user.is_authenticated else 'Anonymous'}"
                )
                
            # Log des requêtes très lentes (> 5s)
            if duration > 5.0:
                logger.error(
                    f"Very slow request: {request.path} - {duration:.2f}s"
                )
                
        return response


class QueryCountMiddleware(MiddlewareMixin):
    """
    Middleware pour monitorer le nombre de requêtes SQL
    """
    
    def process_response(self, request, response):
        if settings.DEBUG:
            # Afficher le nombre de requêtes en mode debug
            total_queries = len(connection.queries)
            if total_queries > 50:
                logger.warning(
                    f"High query count: {request.path} - {total_queries} queries"
                )
                
            # Log des requêtes N+1
            if hasattr(request, '_queries_count'):
                response['X-Query-Count'] = str(total_queries)
                
        return response