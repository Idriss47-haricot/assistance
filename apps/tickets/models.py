from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinLengthValidator, MaxLengthValidator
from django.utils import timezone
from django.contrib.auth import get_user_model
import uuid
import os

User = get_user_model()


# apps/tickets/models.py - Version sans auto-assignation

class Ticket(models.Model):
    """
    Modèle principal de ticket - SANS AUTO-ASSIGNATION
    """
    
    class Priority(models.TextChoices):
        LOW = 'LOW', _('Basse')
        MEDIUM = 'MEDIUM', _('Moyenne')
        HIGH = 'HIGH', _('Haute')
        CRITICAL = 'CRITICAL', _('Critique')
    
    class Status(models.TextChoices):
        OPEN = 'OPEN', _('Ouvert')
        IN_PROGRESS = 'IN_PROGRESS', _('En cours')
        RESOLVED = 'RESOLVED', _('Résolu')
        CLOSED = 'CLOSED', _('Fermé')
    
    class Category(models.TextChoices):
        HARDWARE = 'HARDWARE', _('Matériel')
        SOFTWARE = 'SOFTWARE', _('Logiciel')
        NETWORK = 'NETWORK', _('Réseau')
        ACCESS = 'ACCESS', _('Accès')
        OTHER = 'OTHER', _('Autre')
    
    # Identifiants
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(
        _('Référence'),
        max_length=20,
        unique=True,
        editable=False,
        blank=True,
        help_text=_('Référence unique du ticket (générée automatiquement)')
    )
    
    # Informations principales
    title = models.CharField(
        _('Titre'),
        max_length=200,
        validators=[MinLengthValidator(3)],
        help_text=_('Titre court décrivant le problème')
    )
    description = models.TextField(
        _('Description'),
        help_text=_('Description détaillée du problème')
    )
    
    # Classification
    category = models.CharField(
        _('Catégorie'),
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER
    )
    priority = models.CharField(
        _('Priorité'),
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        help_text=_('Niveau de priorité du ticket')
    )
    status = models.CharField(
        _('Statut'),
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        help_text=_('Statut actuel du ticket')
    )
    
    # Relations
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_tickets',
        verbose_name=_('Créé par')
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets',
        verbose_name=_('Assigné à')
    )
    
    # Dates importantes
    created_at = models.DateTimeField(_('Créé le'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Modifié le'), auto_now=True)
    resolved_at = models.DateTimeField(_('Résolu le'), null=True, blank=True)
    closed_at = models.DateTimeField(_('Fermé le'), null=True, blank=True)
    
    # SLA
    sla_due_date = models.DateTimeField(
        _('Date limite SLA'),
        null=True,
        blank=True,
        help_text=_('Date limite de résolution selon le SLA')
    )
    response_time = models.DurationField(
        _('Temps de réponse'),
        null=True,
        blank=True,
        help_text=_('Temps écoulé avant la première réponse')
    )
    
    # Métadonnées
    is_archived = models.BooleanField(_('Archivé'), default=False)
    ip_address = models.GenericIPAddressField(_('Adresse IP'), null=True, blank=True)
    user_agent = models.TextField(_('User Agent'), blank=True)
    
    class Meta:
        verbose_name = _('Ticket')
        verbose_name_plural = _('Tickets')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['created_by', 'assigned_to']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['priority', 'status']),
            models.Index(fields=['reference']),
        ]
        permissions = [
            ('can_assign_tickets', 'Peut assigner des tickets'),
            ('can_change_status', 'Peut changer le statut'),
            ('can_archive_tickets', 'Peut archiver des tickets'),
        ]
    
    def __str__(self):
        return f"{self.reference} - {self.title[:50]}"
    
    def save(self, *args, **kwargs):
        # Générer la référence si le ticket est nouveau
        if not self.reference:
            year = timezone.now().strftime('%y')
            month = timezone.now().strftime('%m')
            count = Ticket.objects.filter(
                created_at__year=timezone.now().year,
                created_at__month=timezone.now().month
            ).count() + 1
            self.reference = f"T{year}{month}{count:04d}"
        
        # Mettre à jour les dates selon le statut
        if self.status == self.Status.RESOLVED and not self.resolved_at:
            self.resolved_at = timezone.now()
        elif self.status == self.Status.CLOSED and not self.closed_at:
            self.closed_at = timezone.now()
        
        # ⚠️ SUPPRIMER LE CALCUL DU TEMPS DE RÉPONSE (Notification n'existe pas)
        # if not self.response_time and self.status in [self.Status.IN_PROGRESS, self.Status.RESOLVED, self.Status.CLOSED]:
        #     from apps.notifications.models import Notification
        #     first_response = Notification.objects.filter(
        #         ticket=self,
        #         type='RESPONSE',
        #         created_at__isnull=False
        #     ).first()
        #     if first_response:
        #         self.response_time = first_response.created_at - self.created_at
        
        # ⚠️ AUCUNE AUTO-ASSIGNATION ICI
        # if not self.assigned_to:
        #     self.assign_technician(auto=True)
        
        super().save(*args, **kwargs)
    
    @property
    def status_display(self):
        """Retourne le statut en français avec badge HTML"""
        colors = {
            'OPEN': 'secondary',
            'IN_PROGRESS': 'primary',
            'RESOLVED': 'success',
            'CLOSED': 'dark',
        }
        return {
            'label': self.get_status_display(),
            'color': colors.get(self.status, 'secondary')
        }
    
    @property
    def priority_display(self):
        """Retourne la priorité avec badge HTML"""
        colors = {
            'LOW': 'secondary',
            'MEDIUM': 'info',
            'HIGH': 'warning',
            'CRITICAL': 'danger',
        }
        return {
            'label': self.get_priority_display(),
            'color': colors.get(self.priority, 'secondary')
        }
    
    @property
    def is_overdue(self):
        """Vérifie si le ticket est en retard"""
        if not self.sla_due_date:
            return False
        if self.status in [self.Status.RESOLVED, self.Status.CLOSED]:
            return False
        return timezone.now() > self.sla_due_date
    
    def assign_technician(self, auto=True):
        """
        Assigne automatiquement un technicien - DÉSACTIVÉ
        
        Args:
            auto (bool): Si True, assignation automatique, sinon manuelle
        """
        # ⚠️ FONCTION DÉSACTIVÉE - RETOURNE DIRECTEMENT
        return None
        
        # CODE ORIGINAL COMMENTÉ
        """
        from django.db.models import Count
        
        if self.assigned_to:
            return self.assigned_to
        
        technicians = User.objects.filter(
            role__in=['TECHNICIAN', 'MANAGER', 'ADMIN'],
            is_active=True,
            is_available=True
        )
        
        if not technicians.exists():
            return None
        
        if auto:
            technician = technicians.annotate(
                active_count=Count('assigned_tickets', filter=models.Q(
                    assigned_tickets__status__in=['OPEN', 'IN_PROGRESS']
                ))
            ).order_by('active_count').first()
        else:
            technician = technicians.first()
        
        self.assigned_to = technician
        self.save(update_fields=['assigned_to'])
        return technician
        """
    
    def assign_to(self, user):
        """
        Assigner manuellement un ticket à un utilisateur
        """
        if not user.is_staff:
            raise ValueError("Seul un technicien peut être assigné à un ticket")
        
        self.assigned_to = user
        self.status = self.Status.IN_PROGRESS
        self.save()
        return self
    
    def change_status(self, new_status, user=None, comment=None):
        """
        Change le statut du ticket avec validation
        """
        valid_transitions = {
            'OPEN': ['IN_PROGRESS', 'RESOLVED', 'CLOSED'],
            'IN_PROGRESS': ['RESOLVED', 'CLOSED', 'OPEN'],
            'RESOLVED': ['CLOSED', 'OPEN', 'IN_PROGRESS'],
            'CLOSED': ['OPEN'],
        }
        
        if new_status not in dict(self.Status.choices):
            raise ValueError(_('Statut invalide'))
        
        if new_status not in valid_transitions.get(self.status, []):
            raise ValueError(_(f'Transition de {self.get_status_display()} vers {dict(self.Status.choices)[new_status]} non autorisée'))
        
        old_status = self.status
        self.status = new_status
        self.save()
        
        # ⚠️ COMMENTÉ - Notification n'existe pas
        # from apps.notifications.models import Notification
        # Notification.objects.create(
        #     ticket=self,
        #     user=user,
        #     type='STATUS_CHANGE',
        #     message=f"Statut changé de {dict(self.Status.choices)[old_status]} à {dict(self.Status.choices)[new_status]}",
        #     metadata={
        #         'old_status': old_status,
        #         'new_status': new_status,
        #         'changed_by': user.username if user else None
        #     }
        # )
        
        # Ajouter un commentaire si fourni
        if comment:
            Comment.objects.create(
                ticket=self,
                user=user,
                content=f"Changement de statut: {comment}",
                is_internal=True
            )
        
        # ⚠️ COMMENTÉ - Service de notification n'existe pas
        # from apps.notifications.services import send_status_change_notification
        # send_status_change_notification(self, old_status, user)
        
        return True


class Comment(models.Model):
    """
    Modèle de commentaire sur un ticket
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_('Ticket')
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_('Utilisateur')
    )
    
    content = models.TextField(
        _('Contenu'),
        help_text=_('Contenu du commentaire')
    )
    is_internal = models.BooleanField(
        _('Interne'),
        default=False,
        help_text=_('Commentaire visible uniquement par les techniciens')
    )
    
    created_at = models.DateTimeField(_('Créé le'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Modifié le'), auto_now=True)
    
    class Meta:
        verbose_name = _('Commentaire')
        verbose_name_plural = _('Commentaires')
        ordering = ['created_at']
    
    def __str__(self):
        return f"Commentaire de {self.user.username} sur {self.ticket.reference}"
    
    def save(self, *args, **kwargs):
        # Créer une notification
        if not self.pk:  # Nouveau commentaire
            from apps.notifications.models import Notification
            Notification.objects.create(
                ticket=self.ticket,
                user=self.user,
                type='COMMENT',
                message=f"Nouveau commentaire de {self.user.get_full_name()}",
                metadata={
                    'comment_id': str(self.id),
                    'is_internal': self.is_internal
                }
            )
        super().save(*args, **kwargs)


class Attachment(models.Model):
    """
    Modèle de pièce jointe
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name=_('Ticket')
    )
    
    file = models.FileField(
        _('Fichier'),
        upload_to='tickets/%Y/%m/%d/',
        max_length=255
    )
    filename = models.CharField(_('Nom du fichier'), max_length=255)
    mime_type = models.CharField(_('Type MIME'), max_length=100)
    size = models.PositiveIntegerField(_('Taille (octets)'))
    
    uploaded_at = models.DateTimeField(_('Uploadé le'), auto_now_add=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploads',
        verbose_name=_('Uploadé par')
    )
    
    class Meta:
        verbose_name = _('Pièce jointe')
        verbose_name_plural = _('Pièces jointes')
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return self.filename
    
    def save(self, *args, **kwargs):
        if not self.filename:
            self.filename = os.path.basename(self.file.name)
        if not self.mime_type:
            # Essayer de détecter le type MIME
            import mimetypes
            self.mime_type = mimetypes.guess_type(self.filename)[0] or 'application/octet-stream'
        if not self.size:
            self.size = self.file.size
        super().save(*args, **kwargs)


class AuditLog(models.Model):
    """
    Journal d'audit pour tracer toutes les actions
    """
    class ActionType(models.TextChoices):
        CREATE = 'CREATE', _('Création')
        UPDATE = 'UPDATE', _('Modification')
        DELETE = 'DELETE', _('Suppression')
        STATUS_CHANGE = 'STATUS_CHANGE', _('Changement de statut')
        ASSIGN = 'ASSIGN', _('Assignation')
        COMMENT = 'COMMENT', _('Commentaire')
        VIEW = 'VIEW', _('Visualisation')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='audit_logs',
        verbose_name=_('Ticket'),
        null=True,
        blank=True
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs',
        verbose_name=_('Utilisateur')
    )
    
    action = models.CharField(
        _('Action'),
        max_length=20,
        choices=ActionType.choices
    )
    field_name = models.CharField(
        _('Champ'),
        max_length=100,
        blank=True,
        help_text=_('Nom du champ modifié')
    )
    old_value = models.TextField(
        _('Ancienne valeur'),
        blank=True
    )
    new_value = models.TextField(
        _('Nouvelle valeur'),
        blank=True
    )
    ip_address = models.GenericIPAddressField(
        _('Adresse IP'),
        null=True,
        blank=True
    )
    user_agent = models.TextField(
        _('User Agent'),
        blank=True
    )
    
    created_at = models.DateTimeField(_('Créé le'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Journal d\'audit')
        verbose_name_plural = _('Journaux d\'audit')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ticket', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.created_at}"
    


# apps/tickets/models.py - Ajouter dans le modèle Notification

class Notification(models.Model):
    """
    Modèle de notification avec son
    """
    NOTIFICATION_TYPES = [
        ('TICKET_CREATED', '📩 Ticket créé'),
        ('STATUS_CHANGED', '📌 Statut changé'),
        ('ASSIGNED', '📋 Ticket assigné'),
        ('COMMENT_ADDED', '💬 Commentaire ajouté'),
        ('TICKET_RESOLVED', '✅ Ticket résolu'),
        ('TICKET_CLOSED', '🔒 Ticket fermé'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='notifications')
    
    type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=200, blank=True)
    sound = models.CharField(max_length=100, blank=True, default='')  # ← AJOUT : nom du son
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.user.username}"
    
    def mark_as_read(self):
        self.is_read = True
        self.save(update_fields=['is_read'])
    
    @classmethod
    def create_notification(cls, user, ticket, type, message, link=None, sound=None):
        return cls.objects.create(
            user=user,
            ticket=ticket,
            type=type,
            message=message,
            link=link or f'/tickets/{ticket.id}/',
            sound=sound or ''
        )