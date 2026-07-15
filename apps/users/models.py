from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinLengthValidator
import uuid


class User(AbstractUser):
    """
    Modèle utilisateur personnalisé avec rôles et informations supplémentaires
    """
    ROLE_CHOICES = [
        ('EMPLOYEE', 'Employé'),
        ('TECHNICIAN', 'Technicien'),
        ('MANAGER', 'Manager'),
        ('ADMIN', 'Administrateur'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(_('Rôle'), max_length=20, choices=ROLE_CHOICES, default='EMPLOYEE')
    
    # Informations professionnelles
    department = models.CharField(_('Département'), max_length=100, blank=True)
    phone_number = models.CharField(_('Téléphone'), max_length=20, blank=True)
    
    # Informations supplémentaires
    avatar = models.ImageField(_('Avatar'), upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(_('Biographie'), blank=True)
    
    # Disponibilité
    is_available = models.BooleanField(_('Disponible'), default=True)
    
    # Dates importantes
    last_activity = models.DateTimeField(_('Dernière activité'), auto_now=True)
    date_joined = models.DateTimeField(_('Date d\'inscription'), auto_now_add=True)
    
    # Champs pour l'authentification LDAP (bonus)
    ldap_uid = models.CharField(max_length=100, blank=True, null=True, unique=True)
    
    class Meta:
        verbose_name = _('Utilisateur')
        verbose_name_plural = _('Utilisateurs')
        permissions = [
            ('can_manage_users', 'Peut gérer les utilisateurs'),
            ('can_manage_tickets', 'Peut gérer tous les tickets'),
            ('can_view_analytics', 'Peut voir les statistiques'),
        ]
        ordering = ['-date_joined']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"
    
    @property
    def is_technician(self):
        return self.role in ['TECHNICIAN', 'MANAGER', 'ADMIN']
    
    @property
    def is_manager(self):
        return self.role in ['MANAGER', 'ADMIN']
    
    @property
    def is_admin(self):
        return self.role == 'ADMIN'
    
    @property
    def full_name(self):
        return self.get_full_name() or self.username
    
    def get_assigned_tickets_count(self):
        """Nombre de tickets assignés actifs"""
        from apps.tickets.models import Ticket
        return Ticket.objects.filter(
            assigned_to=self,
            status__in=['OPEN', 'IN_PROGRESS']
        ).count()
    
    def get_resolved_tickets_count(self, period=None):
        """Nombre de tickets résolus"""
        from apps.tickets.models import Ticket
        queryset = Ticket.objects.filter(
            assigned_to=self,
            status='RESOLVED'
        )
        if period == 'today':
            from django.utils import timezone
            today = timezone.now().date()
            queryset = queryset.filter(resolved_at__date=today)
        return queryset.count()
    
    def get_average_resolution_time(self):
        """Temps moyen de résolution en heures"""
        from apps.tickets.models import Ticket
        from django.db.models import Avg, F, ExpressionWrapper, fields
        from django.db.models.functions import Extract
        from datetime import timedelta
        
        resolved_tickets = Ticket.objects.filter(
            assigned_to=self,
            status='RESOLVED',
            resolved_at__isnull=False
        )
        
        if not resolved_tickets.exists():
            return None
        
        # Calcul du temps de résolution
        from django.db.models import Sum
        total_time = sum(
            (t.resolved_at - t.created_at).total_seconds() / 3600 
            for t in resolved_tickets
        )
        return round(total_time / resolved_tickets.count(), 2)
    
    def save(self, *args, **kwargs):
        # Si l'utilisateur est superuser, définir le rôle comme ADMIN
        if self.is_superuser:
            self.role = 'ADMIN'
        super().save(*args, **kwargs)