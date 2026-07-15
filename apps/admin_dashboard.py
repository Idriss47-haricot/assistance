# apps/admin_dashboard.py
from django.contrib.admin import AdminSite
from django.template.response import TemplateResponse
from django.db.models import Count, Q
from django.contrib.auth import get_user_model
from apps.tickets.models import Ticket

User = get_user_model()

class HelpdeskAdminSite(AdminSite):
    """
    Site Admin personnalisé avec dashboard
    """
    site_header = "Helpdesk - Administration"
    site_title = "Helpdesk Admin"
    index_title = "Tableau de bord Helpdesk"
    
    def index(self, request, extra_context=None):
        """
        Personnaliser la page d'accueil de l'admin
        """
        # Statistiques
        total_users = User.objects.count()
        total_tickets = Ticket.objects.count()
        open_tickets = Ticket.objects.filter(status='OPEN').count()
        in_progress = Ticket.objects.filter(status='IN_PROGRESS').count()
        resolved = Ticket.objects.filter(status='RESOLVED').count()
        critical = Ticket.objects.filter(priority='CRITICAL').count()
        
        # Tickets récents
        recent_tickets = Ticket.objects.select_related('created_by', 'assigned_to').order_by('-created_at')[:5]
        
        # Techniciens
        technicians = User.objects.filter(role='TECHNICIAN')
        
        context = {
            **self.each_context(request),
            'total_users': total_users,
            'total_tickets': total_tickets,
            'open_tickets': open_tickets,
            'in_progress': in_progress,
            'resolved': resolved,
            'critical': critical,
            'recent_tickets': recent_tickets,
            'technicians': technicians,
        }
        
        if extra_context:
            context.update(extra_context)
        
        return TemplateResponse(request, "admin/dashboard.html", context)