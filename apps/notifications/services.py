# apps/notifications/services.py
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Notification

def send_comment_notification(comment):
    """
    Envoyer une notification par email pour un commentaire
    """
    # Version simplifiée - désactivée pour l'instant
    pass

def send_status_change_notification(ticket, old_status, user):
    """
    Envoyer une notification pour un changement de statut
    """
    pass

def send_assignment_notification(ticket, technician, assigned_by):
    """
    Envoyer une notification pour une assignation
    """
    pass

# apps/notifications/services.py


def send_self_assignment_notification(ticket, technician):
    """
    Crée une notification interne quand un technicien s'auto-assigne un ticket.
    """
    Notification.objects.create(
        ticket=ticket,
        user=technician,
        type='ASSIGN',
        message=f"Vous vous êtes assigné le ticket #{ticket.reference} : « {ticket.title} ».",
        metadata={'self_assigned': True},
    )