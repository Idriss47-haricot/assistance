# apps/tickets/notifications.py
from django.db.models import Q
from .models import Notification, Ticket


class NotificationService:
    """
    Service de gestion des notifications
    """
    
    @classmethod
    def notify_ticket_created(cls, ticket):
        """
        Notifier quand un ticket est créé
        """
        # Notifier tous les techniciens et managers
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        recipients = User.objects.filter(
            Q(is_staff=True) | Q(role='MANAGER'),
            is_active=True
        )
        
        message = f"📝 Nouveau ticket #{ticket.reference} créé par {ticket.created_by.get_full_name() or ticket.created_by.username}"
        
        for user in recipients:
            Notification.create_notification(
                user=user,
                ticket=ticket,
                type='TICKET_CREATED',
                message=message
            )
    
    @classmethod
    def notify_status_changed(cls, ticket, old_status, user):
        """
        Notifier quand le statut d'un ticket change
        """
        status_labels = dict(Ticket.Status.choices)
        
        # Notifier le créateur du ticket
        if ticket.created_by != user:
            message = f"📌 Statut du ticket #{ticket.reference} changé : {status_labels.get(old_status, old_status)} → {status_labels.get(ticket.status, ticket.status)}"
            Notification.create_notification(
                user=ticket.created_by,
                ticket=ticket,
                type='STATUS_CHANGED',
                message=message
            )
        
        # Notifier le technicien assigné (si différent)
        if ticket.assigned_to and ticket.assigned_to != user:
            message = f"📌 Statut du ticket #{ticket.reference} changé par {user.get_full_name() or user.username}"
            Notification.create_notification(
                user=ticket.assigned_to,
                ticket=ticket,
                type='STATUS_CHANGED',
                message=message
            )
    
    @classmethod
    def notify_assigned(cls, ticket, assigned_by):
        """
        Notifier quand un ticket est assigné
        """
        if ticket.assigned_to:
            message = f"📋 Ticket #{ticket.reference} vous a été assigné par {assigned_by.get_full_name() or assigned_by.username}"
            Notification.create_notification(
                user=ticket.assigned_to,
                ticket=ticket,
                type='ASSIGNED',
                message=message
            )
            
            # Notifier le créateur
            if ticket.created_by != ticket.assigned_to:
                message = f"📋 Ticket #{ticket.reference} assigné à {ticket.assigned_to.get_full_name() or ticket.assigned_to.username}"
                Notification.create_notification(
                    user=ticket.created_by,
                    ticket=ticket,
                    type='ASSIGNED',
                    message=message
                )
    
    @classmethod
    def get_unread_count(cls, user):
        """
        Nombre de notifications non lues
        """
        return Notification.objects.filter(user=user, is_read=False).count()
    
    @classmethod
    def get_notifications(cls, user, limit=20):
        """
        Récupérer les notifications d'un utilisateur
        """
        return Notification.objects.filter(user=user)[:limit]
    
    @classmethod
    def mark_all_as_read(cls, user):
        """
        Marquer toutes les notifications comme lues
        """
        Notification.objects.filter(user=user, is_read=False).update(is_read=True)