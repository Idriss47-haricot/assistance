# apps/tickets/dashboard.py
from django.db.models import Count, Q, Avg, Sum, F
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from .models import Ticket, Comment, AuditLog
from django.db.models import Count, Q, Avg, F, Sum
from django.db.models import Count, Q, Avg, F, Sum, Min, Max
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, Extract
from datetime import timedelta, datetime


User = get_user_model()


class DashboardService:
    """
    Service de gestion des statistiques du tableau de bord
    """
    
    @classmethod
    def get_manager_stats(cls):
        """
        Statistiques complètes pour le Manager
        """
        now = timezone.now()
        today = now.date()
        week_start = now - timedelta(days=7)
        
        # Statistiques globales
        total_tickets = Ticket.objects.count()
        open_tickets = Ticket.objects.filter(status='OPEN').count()
        in_progress = Ticket.objects.filter(status='IN_PROGRESS').count()
        resolved_tickets = Ticket.objects.filter(status='RESOLVED').count()
        closed_tickets = Ticket.objects.filter(status='CLOSED').count()
        critical_tickets = Ticket.objects.filter(priority='CRITICAL').count()
        
        # Tickets en attente (non assignés)
        unassigned = Ticket.objects.filter(assigned_to__isnull=True, status='OPEN').count()
        
        # Tickets de la semaine
        tickets_this_week = Ticket.objects.filter(created_at__gte=week_start).count()
        resolved_this_week = Ticket.objects.filter(
            resolved_at__gte=week_start,
            status='RESOLVED'
        ).count()
        
        # Taux de résolution
        resolution_rate = 0
        if total_tickets > 0:
            resolution_rate = round((resolved_tickets / total_tickets) * 100, 1)
        
        # Temps moyen de résolution (en heures)
        avg_resolution = Ticket.objects.filter(
            status='RESOLVED',
            resolved_at__isnull=False
        ).aggregate(
            avg_time=Avg(F('resolved_at') - F('created_at'))
        )['avg_time']
        
        avg_resolution_hours = None
        if avg_resolution:
            avg_resolution_hours = round(avg_resolution.total_seconds() / 3600, 1)
        
        # Tickets par priorité
        priority_stats = {}
        for priority in dict(Ticket.Priority.choices):
            count = Ticket.objects.filter(priority=priority[0]).count()
            priority_stats[priority[0]] = count
        
        # Tickets par statut
        status_stats = {}
        for status in dict(Ticket.Status.choices):
            count = Ticket.objects.filter(status=status[0]).count()
            status_stats[status[0]] = count
        
        # Tickets par catégorie
        category_stats = {}
        for category in dict(Ticket.Category.choices):
            count = Ticket.objects.filter(category=category[0]).count()
            category_stats[category[0]] = count
        
        # Évolution des tickets (7 derniers jours)
        daily_evolution = []
        for i in range(7):
            date = now.date() - timedelta(days=i)
            start = timezone.make_aware(timezone.datetime.combine(date, timezone.datetime.min.time()))
            end = timezone.make_aware(timezone.datetime.combine(date, timezone.datetime.max.time()))
            
            created = Ticket.objects.filter(created_at__range=(start, end)).count()
            resolved = Ticket.objects.filter(resolved_at__range=(start, end)).count()
            
            daily_evolution.append({
                'date': date.strftime('%d/%m'),
                'created': created,
                'resolved': resolved
            })
        daily_evolution.reverse()
        
        return {
            'totals': {
                'total': total_tickets,
                'open': open_tickets,
                'in_progress': in_progress,
                'resolved': resolved_tickets,
                'closed': closed_tickets,
                'critical': critical_tickets,
                'unassigned': unassigned,
            },
            'weekly': {
                'created': tickets_this_week,
                'resolved': resolved_this_week,
            },
            'resolution_rate': resolution_rate,
            'avg_resolution_hours': avg_resolution_hours,
            'priority_stats': priority_stats,
            'status_stats': status_stats,
            'category_stats': category_stats,
            'daily_evolution': daily_evolution,
        }
    
    @classmethod
    def get_technician_performance(cls):
        """
        Performance détaillée des techniciens
        """
        technicians = User.objects.filter(
            role__in=['TECHNICIAN', 'MANAGER'],
            is_active=True
        )
        
        performance_data = []
        
        for tech in technicians:
            # Tickets assignés
            assigned_tickets = Ticket.objects.filter(assigned_to=tech)
            total_assigned = assigned_tickets.count()
            
            # Tickets résolus
            resolved_tickets = assigned_tickets.filter(status='RESOLVED')
            total_resolved = resolved_tickets.count()
            
            # Tickets en cours
            in_progress_count = assigned_tickets.filter(status='IN_PROGRESS').count()
            
            # Temps moyen de résolution
            avg_time = resolved_tickets.aggregate(
                avg_time=Avg(F('resolved_at') - F('created_at'))
            )['avg_time']
            
            avg_hours = None
            if avg_time:
                avg_hours = round(avg_time.total_seconds() / 3600, 1)
            
            # Taux de résolution
            resolution_rate = 0
            if total_assigned > 0:
                resolution_rate = round((total_resolved / total_assigned) * 100, 1)
            
            # Satisfaction (basée sur les commentaires positifs)
            satisfaction_comments = Comment.objects.filter(
                ticket__assigned_to=tech,
                content__icontains='satisfait'
            ).count()
            
            satisfaction_rate = 0
            if total_resolved > 0:
                satisfaction_rate = round((satisfaction_comments / total_resolved) * 100, 1)
            
            # Score de performance (pondéré)
            performance_score = 0
            if total_assigned > 0:
                performance_score = (
                    (total_resolved / total_assigned * 40) +  # 40% poids productivité
                    (50 / (avg_hours + 1) if avg_hours else 0) +  # 30% poids rapidité
                    (satisfaction_rate * 0.3)  # 30% poids satisfaction
                )
                performance_score = round(min(performance_score, 100), 1)
            
            performance_data.append({
                'id': str(tech.id),
                'username': tech.username,
                'full_name': tech.get_full_name() or tech.username,
                'total_assigned': total_assigned,
                'total_resolved': total_resolved,
                'in_progress': in_progress_count,
                'avg_resolution_hours': avg_hours,
                'resolution_rate': resolution_rate,
                'satisfaction_rate': satisfaction_rate,
                'performance_score': performance_score,
            })
        
        # Trier par performance décroissante
        return sorted(performance_data, key=lambda x: x['performance_score'], reverse=True)
    
    @classmethod
    def get_recent_tickets(cls, limit=10):
        """
        Derniers tickets créés
        """
        return Ticket.objects.select_related(
            'created_by', 'assigned_to'
        ).order_by('-created_at')[:limit]
    
    @classmethod
    def get_urgent_tickets(cls):
        """
        Tickets urgents (critiques ou en retard SLA)
        """
        now = timezone.now()
        return Ticket.objects.filter(
            Q(priority='CRITICAL') | Q(
                sla_due_date__lt=now,
                status__in=['OPEN', 'IN_PROGRESS']
            )
        ).select_related('created_by', 'assigned_to')[:10]
    
    @classmethod
    def get_sla_stats(cls):
        """
        Statistiques SLA
        """
        now = timezone.now()
        
        total_with_sla = Ticket.objects.filter(
            sla_due_date__isnull=False
        ).count()
        
        overdue = Ticket.objects.filter(
            sla_due_date__lt=now,
            status__in=['OPEN', 'IN_PROGRESS']
        ).count()
        
        on_track = Ticket.objects.filter(
            sla_due_date__gte=now,
            status__in=['OPEN', 'IN_PROGRESS']
        ).count()
        
        resolved_within_sla = Ticket.objects.filter(
            status='RESOLVED',
            resolved_at__lte=F('sla_due_date')
        ).count()
        
        sla_compliance_rate = 0
        if total_with_sla > 0:
            sla_compliance_rate = round((resolved_within_sla / total_with_sla) * 100, 1)
        
        return {
            'total_with_sla': total_with_sla,
            'overdue': overdue,
            'on_track': on_track,
            'resolved_within_sla': resolved_within_sla,
            'sla_compliance_rate': sla_compliance_rate,
        }
    

    @classmethod
    def get_report_data(cls, start_date=None, end_date=None, technician_id=None):
        """
        Récupère les données pour un rapport de performance
        """
        now = timezone.now()
        
        # Définir la période
        if not start_date:
            start_date = now - timedelta(days=30)
        if not end_date:
            end_date = now
        
        # Filtrer les tickets par période
        tickets = Ticket.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        
        # Filtrer par technicien
        if technician_id:
            tickets = tickets.filter(assigned_to_id=technician_id)
        
        # Statistiques globales
        total_tickets = tickets.count()
        resolved_tickets = tickets.filter(status='RESOLVED').count()
        in_progress = tickets.filter(status='IN_PROGRESS').count()
        open_tickets = tickets.filter(status='OPEN').count()
        closed_tickets = tickets.filter(status='CLOSED').count()
        
        # Taux de résolution
        resolution_rate = 0
        if total_tickets > 0:
            resolution_rate = round((resolved_tickets / total_tickets) * 100, 1)
        
        # Temps moyen de résolution
        avg_time = tickets.filter(
            status='RESOLVED',
            resolved_at__isnull=False
        ).aggregate(
            avg_time=Avg(F('resolved_at') - F('created_at'))
        )['avg_time']
        
        avg_hours = None
        if avg_time:
            avg_hours = round(avg_time.total_seconds() / 3600, 1)
        
        # Tickets par catégorie
        category_stats = {}
        for category in dict(Ticket.Category.choices):
            count = tickets.filter(category=category[0]).count()
            category_stats[category[0]] = count
        
        # Tickets par priorité
        priority_stats = {}
        for priority in dict(Ticket.Priority.choices):
            count = tickets.filter(priority=priority[0]).count()
            priority_stats[priority[0]] = count
        
        # Tickets en retard SLA
        overdue_tickets = tickets.filter(
            sla_due_date__lt=timezone.now(),
            status__in=['OPEN', 'IN_PROGRESS']
        )
        
        # Conformité SLA
        total_sla = tickets.filter(sla_due_date__isnull=False).count()
        sla_compliant = tickets.filter(
            status='RESOLVED',
            resolved_at__lte=F('sla_due_date')
        ).count()
        
        sla_rate = 0
        if total_sla > 0:
            sla_rate = round((sla_compliant / total_sla) * 100, 1)
        
        # Performance des techniciens
        technicians = User.objects.filter(
            is_staff=True,
            is_active=True
        )
        
        technician_performance = []
        for tech in technicians:
            tech_tickets = tickets.filter(assigned_to=tech)
            tech_total = tech_tickets.count()
            tech_resolved = tech_tickets.filter(status='RESOLVED').count()
            
            tech_avg_time = tech_tickets.filter(
                status='RESOLVED',
                resolved_at__isnull=False
            ).aggregate(
                avg_time=Avg(F('resolved_at') - F('created_at'))
            )['avg_time']
            
            tech_avg_hours = None
            if tech_avg_time:
                tech_avg_hours = round(tech_avg_time.total_seconds() / 3600, 1)
            
            tech_rate = 0
            if tech_total > 0:
                tech_rate = round((tech_resolved / tech_total) * 100, 1)
            
            # Satisfaction (commentaires positifs)
            satisfaction = Comment.objects.filter(
                ticket__assigned_to=tech,
                content__icontains='satisfait'
            ).count()
            
            satisfaction_rate = 0
            if tech_resolved > 0:
                satisfaction_rate = round((satisfaction / tech_resolved) * 100, 1)
            
            # Score de performance
            performance_score = 0
            if tech_total > 0:
                performance_score = (
                    (tech_rate * 0.4) +
                    (50 / (tech_avg_hours + 1) if tech_avg_hours else 0) +
                    (satisfaction_rate * 0.3)
                )
                performance_score = round(min(performance_score, 100), 1)
            
            technician_performance.append({
                'id': str(tech.id),
                'name': tech.get_full_name() or tech.username,
                'total_assigned': tech_total,
                'total_resolved': tech_resolved,
                'avg_resolution_hours': tech_avg_hours,
                'resolution_rate': tech_rate,
                'satisfaction_rate': satisfaction_rate,
                'performance_score': performance_score,
            })
        
        # Trier par performance
        technician_performance.sort(key=lambda x: x['performance_score'], reverse=True)
        
        # Évolution quotidienne (derniers 30 jours)
        daily_evolution = []
        for i in range(30, -1, -1):
            date = now.date() - timedelta(days=i)
            start = timezone.make_aware(timezone.datetime.combine(date, timezone.datetime.min.time()))
            end = timezone.make_aware(timezone.datetime.combine(date, timezone.datetime.max.time()))
            
            created = tickets.filter(created_at__range=(start, end)).count()
            resolved = tickets.filter(resolved_at__range=(start, end)).count()
            
            daily_evolution.append({
                'date': date.strftime('%d/%m'),
                'created': created,
                'resolved': resolved
            })
        
        return {
            'summary': {
                'total': total_tickets,
                'resolved': resolved_tickets,
                'in_progress': in_progress,
                'open': open_tickets,
                'closed': closed_tickets,
                'resolution_rate': resolution_rate,
                'avg_resolution_hours': avg_hours,
                'sla_rate': sla_rate,
            },
            'category_stats': category_stats,
            'priority_stats': priority_stats,
            'technician_performance': technician_performance,
            'daily_evolution': daily_evolution,
            'overdue_tickets': overdue_tickets[:10],
            'period': {
                'start': start_date.strftime('%d/%m/%Y'),
                'end': end_date.strftime('%d/%m/%Y'),
            }
        }
    

    @classmethod

    def get_advanced_stats(cls, period='month'):
        """
        Récupère les statistiques avancées avec comparaison
        """
        now = timezone.now()
        
        # Définir les périodes
        if period == 'week':
            current_start = now - timedelta(days=7)
            previous_start = now - timedelta(days=14)
            previous_end = now - timedelta(days=7)
            date_format = '%d/%m'
        elif period == 'month':
            current_start = now - timedelta(days=30)
            previous_start = now - timedelta(days=60)
            previous_end = now - timedelta(days=30)
            date_format = '%d/%m'
        else:  # year
            current_start = now - timedelta(days=365)
            previous_start = now - timedelta(days=730)
            previous_end = now - timedelta(days=365)
            date_format = '%m/%Y'
        
        # === STATISTIQUES GLOBALES ===
        # Période actuelle
        current_tickets = Ticket.objects.filter(created_at__gte=current_start)
        current_total = current_tickets.count()
        current_resolved = current_tickets.filter(status='RESOLVED').count()
        current_in_progress = current_tickets.filter(status='IN_PROGRESS').count()
        current_open = current_tickets.filter(status='OPEN').count()
        current_closed = current_tickets.filter(status='CLOSED').count()
        current_critical = current_tickets.filter(priority='CRITICAL').count()
        
        # Période précédente
        previous_tickets = Ticket.objects.filter(
            created_at__gte=previous_start,
            created_at__lt=previous_end
        )
        previous_total = previous_tickets.count()
        previous_resolved = previous_tickets.filter(status='RESOLVED').count()
        previous_in_progress = previous_tickets.filter(status='IN_PROGRESS').count()
        previous_open = previous_tickets.filter(status='OPEN').count()
        previous_closed = previous_tickets.filter(status='CLOSED').count()
        previous_critical = previous_tickets.filter(priority='CRITICAL').count()
        
        # Calcul des variations
        def calc_variation(current, previous):
            if previous == 0:
                return 100 if current > 0 else 0
            return round(((current - previous) / previous) * 100, 1)
        
        # === TEMPS MOYEN DE RÉSOLUTION ===
        avg_resolution = current_tickets.filter(
            status='RESOLVED',
            resolved_at__isnull=False
        ).aggregate(
            avg_time=Avg(F('resolved_at') - F('created_at'))
        )['avg_time']
        
        avg_hours = None
        if avg_resolution:
            avg_hours = round(avg_resolution.total_seconds() / 3600, 1)
        
        # === TAUX DE RÉSOLUTION ===
        resolution_rate = 0
        if current_total > 0:
            resolution_rate = round((current_resolved / current_total) * 100, 1)
        
        # === SLA ===
        total_sla = current_tickets.filter(sla_due_date__isnull=False).count()
        sla_compliant = current_tickets.filter(
            status='RESOLVED',
            resolved_at__lte=F('sla_due_date')
        ).count()
        
        sla_rate = 0
        if total_sla > 0:
            sla_rate = round((sla_compliant / total_sla) * 100, 1)
        
        overdue = current_tickets.filter(
            sla_due_date__lt=now,
            status__in=['OPEN', 'IN_PROGRESS']
        ).count()
        
        # === PERFORMANCE DES TECHNICIENS ===
        technicians = User.objects.filter(
            is_staff=True,
            is_active=True
        )
        
        technician_stats = []
        for tech in technicians:
            tech_tickets = current_tickets.filter(assigned_to=tech)
            tech_total = tech_tickets.count()
            tech_resolved = tech_tickets.filter(status='RESOLVED').count()
            
            tech_avg = tech_tickets.filter(
                status='RESOLVED',
                resolved_at__isnull=False
            ).aggregate(
                avg_time=Avg(F('resolved_at') - F('created_at'))
            )['avg_time']
            
            tech_avg_hours = None
            if tech_avg:
                tech_avg_hours = round(tech_avg.total_seconds() / 3600, 1)
            
            tech_rate = 0
            if tech_total > 0:
                tech_rate = round((tech_resolved / tech_total) * 100, 1)
            
            # Satisfaction
            satisfaction = Comment.objects.filter(
                ticket__assigned_to=tech,
                content__icontains='satisfait'
            ).count()
            
            satisfaction_rate = 0
            if tech_resolved > 0:
                satisfaction_rate = round((satisfaction / tech_resolved) * 100, 1)
            
            # Score de performance
            performance_score = 0
            if tech_total > 0:
                performance_score = (
                    (tech_rate * 0.4) +
                    (50 / (tech_avg_hours + 1) if tech_avg_hours else 0) +
                    (satisfaction_rate * 0.3)
                )
                performance_score = round(min(performance_score, 100), 1)
            
            technician_stats.append({
                'id': str(tech.id),
                'name': tech.get_full_name() or tech.username,
                'total': tech_total,
                'resolved': tech_resolved,
                'avg_hours': tech_avg_hours,
                'rate': tech_rate,
                'satisfaction': satisfaction_rate,
                'score': performance_score,
            })
        
        technician_stats.sort(key=lambda x: x['score'], reverse=True)
        
        # === STATISTIQUES PAR CATÉGORIE ===
        category_stats = {}
        for category in dict(Ticket.Category.choices):
            count = current_tickets.filter(category=category[0]).count()
            category_stats[category[0]] = count
        
        # === STATISTIQUES PAR PRIORITÉ ===
        priority_stats = {}
        for priority in dict(Ticket.Priority.choices):
            count = current_tickets.filter(priority=priority[0]).count()
            priority_stats[priority[0]] = count
        
        # === ÉVOLUTION QUOTIDIENNE ===
        days = 30 if period != 'year' else 365
        daily_data = []
        for i in range(days, -1, -1):
            date = now.date() - timedelta(days=i)
            start = timezone.make_aware(datetime.combine(date, datetime.min.time()))
            end = timezone.make_aware(datetime.combine(date, datetime.max.time()))
            
            created = Ticket.objects.filter(created_at__range=(start, end)).count()
            resolved = Ticket.objects.filter(resolved_at__range=(start, end)).count()
            
            daily_data.append({
                'date': date.strftime('%d/%m'),
                'created': created,
                'resolved': resolved,
            })
        
        # === TICKETS RÉCENTS ===
        recent_tickets = current_tickets.select_related(
            'created_by', 'assigned_to'
        ).order_by('-created_at')[:10]
        
        # === TICKETS EN RETARD ===
        overdue_tickets = current_tickets.filter(
            sla_due_date__lt=now,
            status__in=['OPEN', 'IN_PROGRESS']
        ).select_related('created_by', 'assigned_to')[:10]
        
        return {
            'period': period,
            'totals': {
                'total': current_total,
                'resolved': current_resolved,
                'in_progress': current_in_progress,
                'open': current_open,
                'closed': current_closed,
                'critical': current_critical,
            },
            'variations': {
                'total': calc_variation(current_total, previous_total),
                'resolved': calc_variation(current_resolved, previous_resolved),
                'in_progress': calc_variation(current_in_progress, previous_in_progress),
                'open': calc_variation(current_open, previous_open),
                'critical': calc_variation(current_critical, previous_critical),
            },
            'avg_resolution_hours': avg_hours,
            'resolution_rate': resolution_rate,
            'sla': {
                'rate': sla_rate,
                'overdue': overdue,
                'total': total_sla,
            },
            'technicians': technician_stats,
            'categories': category_stats,
            'priorities': priority_stats,
            'daily_evolution': daily_data,
            'recent_tickets': recent_tickets,
            'overdue_tickets': overdue_tickets,
        }