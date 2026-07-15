# apps/tickets/signals.py - Version sans auto-assignation
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Ticket

# ⚠️ IMPORT SUPPRIMÉ - plus besoin de TicketAssignmentService
# from .services import TicketAssignmentService


# ⚠️ SIGNAL D'AUTO-ASSIGNATION - COMPLÈTEMENT SUPPRIMÉ
"""
@receiver(post_save, sender=Ticket)
def auto_assign_ticket(sender, instance, created, **kwargs):
    \"\"\"
    Signal pour auto-assigner les tickets à la création - DÉSACTIVÉ
    \"\"\"
    if created and not instance.assigned_to:
        TicketAssignmentService.auto_assign(instance)
"""


# ⚠️ SIGNAL DE CACHE - DÉSACTIVÉ (car invalidate_cache n'existe pas)
"""
from apps.common.decorators import invalidate_cache

@receiver(post_save, sender=Ticket)
@receiver(post_delete, sender=Ticket)
def invalidate_ticket_cache(sender, **kwargs):
    \"\"\"
    Invalide le cache lors de la modification d'un ticket
    \"\"\"
    invalidate_cache('ticket_list')
    invalidate_cache('dashboard_stats')
"""


# ✅ Si vous voulez garder le cache, voici une version simplifiée
# from django.core.cache import cache
# 
# @receiver(post_save, sender=Ticket)
# @receiver(post_delete, sender=Ticket)
# def invalidate_ticket_cache(sender, **kwargs):
#     \"\"\"
#     Invalide le cache lors de la modification d'un ticket
#     \"\"\"
#     cache.delete('ticket_list')
#     cache.delete('dashboard_stats')