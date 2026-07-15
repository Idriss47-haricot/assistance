# apps/notifications/models.py - VERSION FINALE
from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class Notification(models.Model):
    """
    Modèle de notification - UNIQUEMENT CE MODÈLE
    """
    NOTIFICATION_TYPES = [
        ('TICKET_CREATED', '📝 Ticket créé'),
        ('STATUS_CHANGED', '📌 Statut changé'),
        ('ASSIGNED', '📋 Ticket assigné'),
        ('TAKEN', '🔧 Ticket pris'),
        ('COMMENT_ADDED', '💬 Commentaire ajouté'),
        ('TICKET_RESOLVED', '✅ Ticket résolu'),
        ('TICKET_CLOSED', '🔒 Ticket fermé'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relations avec related_name UNIQUES
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='notifications_received'  # ← UNIQUE
    )
    ticket = models.ForeignKey(
        'tickets.Ticket', 
        on_delete=models.CASCADE, 
        related_name='notifications_ticket'  # ← UNIQUE
    )
    
    type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=200, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.user.username}"
    
    def mark_as_read(self):
        self.is_read = True
        self.save(update_fields=['is_read'])
    
    @classmethod
    def create_notification(cls, user, ticket, type, message, link=None):
        return cls.objects.create(
            user=user,
            ticket=ticket,
            type=type,
            message=message,
            link=link or f'/tickets/{ticket.id}/'
        )