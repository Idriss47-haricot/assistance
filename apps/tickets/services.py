from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from typing import Optional, Dict, Any
from .models import Notification
from .models import Ticket, Comment, AuditLog
from django.db.models import Q


User = get_user_model()


class TicketWorkflowService:
    """
    Service de gestion du workflow des tickets
    """
    
    # Définition des transitions valides
    TRANSITIONS = {
        'OPEN': {
            'allowed': ['IN_PROGRESS', 'RESOLVED', 'CLOSED'],
            'requires_permission': False,
            'requires_assignment': False,
        },
        'IN_PROGRESS': {
            'allowed': ['RESOLVED', 'CLOSED', 'OPEN'],
            'requires_permission': True,
            'requires_assignment': True,
        },
        'RESOLVED': {
            'allowed': ['CLOSED', 'OPEN', 'IN_PROGRESS'],
            'requires_permission': True,
            'requires_assignment': False,
            'validation': 'validate_resolved'
        },
        'CLOSED': {
            'allowed': ['OPEN'],
            'requires_permission': True,
            'requires_assignment': False,
        },
    }
    
    @classmethod
    def validate_transition(cls, ticket: Ticket, new_status: str, user: User) -> Dict[str, Any]:
        """
        Valide si la transition est autorisée
        Retourne un dictionnaire avec le statut de validation
        """
        current_status = ticket.status
        
        # Vérifier si le statut existe
        if new_status not in dict(Ticket.Status.choices):
            return {
                'valid': False,
                'error': f"Statut '{new_status}' invalide."
            }
        
        # Vérifier si la transition est autorisée
        if current_status not in cls.TRANSITIONS:
            return {
                'valid': False,
                'error': f"Statut actuel '{current_status}' invalide."
            }
        
        transition = cls.TRANSITIONS[current_status]
        if new_status not in transition['allowed']:
            return {
                'valid': False,
                'error': f"Transition impossible de '{current_status}' vers '{new_status}'."
            }
        
        # Vérifier les permissions
        if transition['requires_permission']:
            # Simplification : vérifier si l'utilisateur est staff ou superuser
            if not (user.is_superuser or user.is_staff):
                return {
                    'valid': False,
                    'error': "Vous n'avez pas la permission d'effectuer cette transition."
                }
        
        # Vérifier l'assignation
        if transition['requires_assignment'] and not ticket.assigned_to:
            return {
                'valid': False,
                'error': "Le ticket doit être assigné à un technicien pour cette transition."
            }
        
        # Validation spécifique par statut
        if 'validation' in transition:
            validation_method = getattr(cls, transition['validation'], None)
            if validation_method:
                validation_result = validation_method(ticket)
                if not validation_result['valid']:
                    return validation_result
        
        return {'valid': True, 'error': None}
    
    @classmethod
    def validate_resolved(cls, ticket: Ticket) -> Dict[str, Any]:
        """
        Validation spécifique pour le statut RESOLVED
        """
        # Vérifier qu'au moins un commentaire de résolution existe
        # CORRECTION : Un seul filtre par appel
        has_resolution_comment = ticket.comments.filter(
            content__icontains='résolu'
        ).exists()
        
        # Si pas trouvé avec "résolu", essayer avec "solution"
        if not has_resolution_comment:
            has_resolution_comment = ticket.comments.filter(
                content__icontains='solution'
            ).exists()
        
        if not has_resolution_comment:
            return {
                'valid': False,
                'error': "Veuillez ajouter un commentaire décrivant la solution avant de résoudre le ticket."
            }
        
        return {'valid': True, 'error': None}
    
    @classmethod
    @transaction.atomic
    def change_status(
        cls, 
        ticket: Ticket, 
        new_status: str, 
        user: User, 
        comment: Optional[str] = None
    ) -> Ticket:
        """
        Change le statut du ticket avec toutes les validations
        """
        # Valider la transition
        validation = cls.validate_transition(ticket, new_status, user)
        if not validation['valid']:
            raise ValidationError(validation['error'])
        
        old_status = ticket.status
        
        # Mettre à jour le statut
        ticket.status = new_status
        
        # Mettre à jour les dates
        if new_status == 'RESOLVED' and not ticket.resolved_at:
            ticket.resolved_at = timezone.now()
        elif new_status == 'CLOSED' and not ticket.closed_at:
            ticket.closed_at = timezone.now()
        
        # Sauvegarder
        ticket.save()
        
        # Ajouter un commentaire automatique
        status_label = dict(Ticket.Status.choices)[new_status]
        comment_content = f"Statut changé : {dict(Ticket.Status.choices)[old_status]} → {status_label}"
        if comment:
            comment_content += f"\n\n{comment}"
        
        Comment.objects.create(
            ticket=ticket,
            user=user,
            content=comment_content,
            is_internal=True
        )
        
        # Audit log
        AuditLog.objects.create(
            ticket=ticket,
            user=user,
            action='STATUS_CHANGE',
            old_value=dict(Ticket.Status.choices)[old_status],
            new_value=dict(Ticket.Status.choices)[new_status],
            field_name='status'
        )
        
        return ticket
    
    @classmethod
    def get_allowed_transitions(cls, ticket: Ticket, user: User) -> list:
        """
        Retourne les transitions autorisées pour un utilisateur donné
        """
        allowed = []
        
        if ticket.status not in cls.TRANSITIONS:
            return allowed
        
        for status in cls.TRANSITIONS[ticket.status]['allowed']:
            validation = cls.validate_transition(ticket, status, user)
            if validation['valid']:
                allowed.append({
                    'value': status,
                    'label': dict(Ticket.Status.choices)[status],
                })
        
        return allowed


class TicketAssignmentService:
    """
    Service d'assignation des tickets
    """
    
    @classmethod
    def auto_assign(cls, ticket: Ticket) -> Optional[User]:
        """
        Assignation automatique avec algorithme Round-Robin
        """
        # Récupérer les techniciens disponibles
        technicians = User.objects.filter(
            is_staff=True,
            is_active=True
        )
        
        if not technicians.exists():
            return None
        
        # Algorithme : charge minimale
        technician = technicians.annotate(
            active_count=Count('assigned_tickets', filter=Q(
                assigned_tickets__status__in=['OPEN', 'IN_PROGRESS']
            ))
        ).order_by('active_count').first()
        
        ticket.assigned_to = technician
        ticket.save()
        
        # Audit log
        AuditLog.objects.create(
            ticket=ticket,
            user=None,  # Automatique
            action='ASSIGN',
            new_value=f"Assigné automatiquement à {technician.get_full_name() or technician.username}",
        )
        
        return technician
    
    @classmethod
    def manual_assign(cls, ticket: Ticket, technician: User, assigned_by: User) -> User:
        """
        Assignation manuelle
        """
        old_assigned_to = ticket.assigned_to
        
        ticket.assigned_to = technician
        ticket.save()
        
        # Audit log
        AuditLog.objects.create(
            ticket=ticket,
            user=assigned_by,
            action='ASSIGN',
            old_value=str(old_assigned_to) if old_assigned_to else 'Non assigné',
            new_value=str(technician),
            field_name='assigned_to'
        )
        
        return technician
    
    @classmethod
    def unassign(cls, ticket: Ticket, user: User) -> None:
        """
        Désassignation du ticket
        """
        old_assigned_to = ticket.assigned_to
        
        ticket.assigned_to = None
        ticket.save()
        
        # Audit log
        AuditLog.objects.create(
            ticket=ticket,
            user=user,
            action='ASSIGN',
            old_value=str(old_assigned_to) if old_assigned_to else 'Non assigné',
            new_value='Désassigné',
            field_name='assigned_to'
        )
    
    @classmethod
    def get_technician_stats(cls) -> list:
        """
        Statistiques des techniciens (charge de travail)
        """
        technicians = User.objects.filter(
            is_staff=True,
            is_active=True
        ).annotate(
            open_count=Count('assigned_tickets', filter=Q(
                assigned_tickets__status='OPEN'
            )),
            in_progress_count=Count('assigned_tickets', filter=Q(
                assigned_tickets__status='IN_PROGRESS'
            )),
            total_active=Count('assigned_tickets', filter=Q(
                assigned_tickets__status__in=['OPEN', 'IN_PROGRESS']
            )),
        ).order_by('total_active')
        
        return [{
            'id': tech.id,
            'name': tech.get_full_name() or tech.username,
            'open_count': tech.open_count,
            'in_progress_count': tech.in_progress_count,
            'total_active': tech.total_active,
            'is_available': getattr(tech, 'is_available', True),
        } for tech in technicians]


class NotificationService:
    """Service de gestion des notifications avec sons"""

    @classmethod
    def notify_ticket_created(cls, ticket):
        """Notifier quand un ticket est créé"""
        recipients = User.objects.filter(
            Q(is_staff=True) | Q(role='MANAGER'),
            is_active=True
        )
        
        message = f"📩 Nouveau ticket #{ticket.reference} créé par {ticket.created_by.get_full_name() or ticket.created_by.username}"
        sound = 'notification-ticket.mp3'
        
        for user in recipients:
            Notification.create_notification(
                user=user,
                ticket=ticket,
                type='TICKET_CREATED',
                message=message,
                sound=sound
            )

    @classmethod
    def notify_status_changed(cls, ticket, old_status, user):
        """Notifier quand le statut change"""
        status_labels = dict(ticket.Status.choices)
        
        if ticket.created_by != user:
            message = f"📌 Ticket #{ticket.reference} : {status_labels.get(old_status, old_status)} → {status_labels.get(ticket.status, ticket.status)}"
            Notification.create_notification(
                user=ticket.created_by,
                ticket=ticket,
                type='STATUS_CHANGED',
                message=message,
                sound='notification-status.mp3'
            )
        
        if ticket.assigned_to and ticket.assigned_to != user:
            message = f"📌 Ticket #{ticket.reference} changé par {user.get_full_name() or user.username}"
            Notification.create_notification(
                user=ticket.assigned_to,
                ticket=ticket,
                type='STATUS_CHANGED',
                message=message,
                sound='notification-status.mp3'
            )

    @classmethod
    def notify_assigned(cls, ticket, assigned_by):
        """Notifier quand un ticket est assigné"""
        if ticket.assigned_to:
            message = f"📋 Ticket #{ticket.reference} assigné par {assigned_by.get_full_name() or assigned_by.username}"
            Notification.create_notification(
                user=ticket.assigned_to,
                ticket=ticket,
                type='ASSIGNED',
                message=message,
                sound='notification-assign.mp3'
            )
            
            if ticket.created_by != ticket.assigned_to:
                message = f"📋 Ticket #{ticket.reference} assigné à {ticket.assigned_to.get_full_name() or ticket.assigned_to.username}"
                Notification.create_notification(
                    user=ticket.created_by,
                    ticket=ticket,
                    type='ASSIGNED',
                    message=message,
                    sound='notification-assign.mp3'
                )

    @classmethod
    def notify_comment_added(cls, comment):
        """Notifier quand un commentaire est ajouté"""
        if comment.ticket.assigned_to:
            message = f"💬 Commentaire de {comment.user.get_full_name() or comment.user.username} sur #{comment.ticket.reference}"
            Notification.create_notification(
                user=comment.ticket.assigned_to,
                ticket=comment.ticket,
                type='COMMENT_ADDED',
                message=message,
                sound='notification-comment.mp3'
            )

    @classmethod
    def get_unread_count(cls, user):
        return Notification.objects.filter(user=user, is_read=False).count()

    @classmethod
    def get_notifications(cls, user, limit=10):
        return Notification.objects.filter(user=user)[:limit]

    @classmethod
    def mark_all_as_read(cls, user):
        Notification.objects.filter(user=user, is_read=False).update(is_read=True)