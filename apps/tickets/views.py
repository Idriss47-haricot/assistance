# apps/tickets/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse, HttpResponse, FileResponse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from django.core.exceptions import ValidationError
import json
import csv
from io import BytesIO
from datetime import datetime

from .models import Ticket, Comment, Attachment, AuditLog
from .forms import (
    TicketCreateForm, TicketEditForm, TicketStatusForm,
    CommentForm, TicketSearchForm
)
from .dashboard import DashboardService
from apps.users.models import User
from django.template.loader import get_template
from datetime import datetime, timedelta



# ============================================================
# EXPORT PDF
# ============================================================

@login_required
def ticket_export_pdf(request):
    """
    Export des tickets en PDF
    """
    if not request.user.is_admin and not request.user.is_manager:
        messages.error(request, _('Vous n\'avez pas la permission d\'exporter les tickets.'))
        return redirect('tickets:list')
    
    # Récupérer les tickets avec les filtres
    tickets = Ticket.objects.select_related('created_by', 'assigned_to').order_by('-created_at')
    
    # Appliquer les filtres de recherche (si présents)
    search_form = TicketSearchForm(request.GET)
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search')
        if search_query:
            tickets = tickets.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(reference__icontains=search_query)
            )
        
        status = search_form.cleaned_data.get('status')
        if status:
            tickets = tickets.filter(status=status)
        
        priority = search_form.cleaned_data.get('priority')
        if priority:
            tickets = tickets.filter(priority=priority)
        
        category = search_form.cleaned_data.get('category')
        if category:
            tickets = tickets.filter(category=category)
        
        assigned_to = search_form.cleaned_data.get('assigned_to')
        if assigned_to:
            tickets = tickets.filter(assigned_to_id=assigned_to)
        
        date_from = search_form.cleaned_data.get('date_from')
        if date_from:
            tickets = tickets.filter(created_at__date__gte=date_from)
        
        date_to = search_form.cleaned_data.get('date_to')
        if date_to:
            tickets = tickets.filter(created_at__date__lte=date_to)
    
    # Créer le buffer pour le PDF
    buffer = BytesIO()
    
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        
        # Créer le document PDF en mode paysage
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=1*cm,
            leftMargin=1*cm,
            topMargin=1*cm,
            bottomMargin=1*cm
        )
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=20,
            textColor=colors.HexColor('#007bff')
        )
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER,
            textColor=colors.white,
            backColor=colors.HexColor('#007bff')
        )
        cell_style = ParagraphStyle(
            'CellStyle',
            parent=styles['Normal'],
            fontSize=8,
            alignment=TA_LEFT,
            leading=12
        )
        
        # Liste des éléments
        elements = []
        
        # Titre
        elements.append(Paragraph("Liste des tickets - Helpdesk", title_style))
        elements.append(Spacer(1, 0.5*cm))
        
        # Informations de filtre
        filter_text = f"Total: {tickets.count()} tickets"
        if request.GET.get('status'):
            filter_text += f" | Statut: {request.GET.get('status')}"
        if request.GET.get('priority'):
            filter_text += f" | Priorité: {request.GET.get('priority')}"
        elements.append(Paragraph(filter_text, styles['Normal']))
        elements.append(Spacer(1, 0.5*cm))
        
        # Préparer les données du tableau
        data = []
        
        # En-têtes
        headers = [
            'Référence', 'Titre', 'Catégorie', 'Priorité', 
            'Statut', 'Créé par', 'Assigné à', 'Créé le', 'Résolu le'
        ]
        data.append([Paragraph(h, header_style) for h in headers])
        
        # Données
        for ticket in tickets:
            row = [
                Paragraph(ticket.reference, cell_style),
                Paragraph(ticket.title[:50], cell_style),
                Paragraph(ticket.get_category_display(), cell_style),
                Paragraph(ticket.get_priority_display(), cell_style),
                Paragraph(ticket.get_status_display(), cell_style),
                Paragraph(ticket.created_by.get_full_name() or ticket.created_by.username, cell_style),
                Paragraph(ticket.assigned_to.get_full_name() if ticket.assigned_to else 'Non assigné', cell_style),
                Paragraph(ticket.created_at.strftime('%d/%m/%Y %H:%M'), cell_style),
                Paragraph(ticket.resolved_at.strftime('%d/%m/%Y %H:%M') if ticket.resolved_at else '-', cell_style),
            ]
            data.append(row)
        
        # Créer le tableau
        table = Table(data, repeatRows=1)
        
        # Style du tableau
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#007bff')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('LEADING', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('WORDWRAP', (0, 0), (-1, -1), 'CJK'),
        ]))
        
        # Alterner les couleurs des lignes
        for i in range(1, len(data)):
            if i % 2 == 0:
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, i), (-1, i), colors.lightgrey),
                ]))
        
        elements.append(table)
        
        # Pied de page
        elements.append(Spacer(1, 0.5*cm))
        footer = Paragraph(
            f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} | Helpdesk v1.0",
            styles['Normal']
        )
        elements.append(footer)
        
        # Construire le PDF
        doc.build(elements)
        
        # Retourner le PDF
        buffer.seek(0)
        return FileResponse(
            buffer,
            as_attachment=True,
            filename=f"tickets_export_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            content_type='application/pdf'
        )
        
    except ImportError:
        messages.error(request, 'La bibliothèque ReportLab n\'est pas installée. Installez-la avec: pip install reportlab')
        return redirect('tickets:list')
    except Exception as e:
        messages.error(request, f'Erreur lors de la génération du PDF: {str(e)}')
        return redirect('tickets:list')


# ============================================================
# LISTE DES TICKETS
# ============================================================

@login_required
def ticket_list(request):
    """
    Liste des tickets avec filtres et pagination
    """
    tickets = Ticket.objects.select_related(
        'created_by', 'assigned_to'
    ).prefetch_related(
        'comments', 'attachments'
    )

    # Filtrer selon le rôle
    if not request.user.is_admin and not request.user.is_manager:
        if request.user.is_technician:
            pass  # Les techniciens voient tous les tickets
        else:
            tickets = tickets.filter(
                Q(created_by=request.user) | Q(assigned_to=request.user)
            )

    # Formulaire de recherche
    search_form = TicketSearchForm(request.GET)

    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search')
        if search_query:
            tickets = tickets.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(reference__icontains=search_query)
            )

        status = search_form.cleaned_data.get('status')
        if status:
            tickets = tickets.filter(status=status)

        priority = search_form.cleaned_data.get('priority')
        if priority:
            tickets = tickets.filter(priority=priority)

        category = search_form.cleaned_data.get('category')
        if category:
            tickets = tickets.filter(category=category)

        assigned_to = search_form.cleaned_data.get('assigned_to')
        if assigned_to:
            tickets = tickets.filter(assigned_to_id=assigned_to)

        date_from = search_form.cleaned_data.get('date_from')
        if date_from:
            tickets = tickets.filter(created_at__date__gte=date_from)

        date_to = search_form.cleaned_data.get('date_to')
        if date_to:
            tickets = tickets.filter(created_at__date__lte=date_to)

    # Tri
    sort_by = request.GET.get('sort', '-created_at')
    allowed_sort = ['created_at', '-created_at', 'priority', '-priority', 'status', 'title']
    effective_sort = sort_by if sort_by in allowed_sort else '-created_at'

    if request.user.is_technician and not (request.user.is_admin or request.user.is_manager):
        tickets = tickets.order_by('assigned_to_id', effective_sort)
    else:
        tickets = tickets.order_by(effective_sort)

    # Statistiques
    stats = {
        'total': tickets.count(),
        'unassigned': tickets.filter(assigned_to__isnull=True).count(),
        'open': tickets.filter(status='OPEN').count(),
        'in_progress': tickets.filter(status='IN_PROGRESS').count(),
        'resolved': tickets.filter(status='RESOLVED').count(),
        'closed': tickets.filter(status='CLOSED').count(),
        'critical': tickets.filter(priority='CRITICAL').count(),
    }

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(tickets, 20)

    try:
        tickets_page = paginator.page(page)
    except PageNotAnInteger:
        tickets_page = paginator.page(1)
    except EmptyPage:
        tickets_page = paginator.page(paginator.num_pages)

    context = {
        'tickets': tickets_page,
        'search_form': search_form,
        'stats': stats,
        'is_technician': request.user.is_technician,
        'is_admin': request.user.is_admin,
    }

    return render(request, 'tickets/list.html', context)


# ============================================================
# CRÉATION D'UN TICKET
# ============================================================

@login_required
def ticket_create(request):
    """
    Création d'un nouveau ticket - SANS AUTO-ASSIGNATION
    """
    if request.method == 'POST':
        form = TicketCreateForm(request.POST, request.FILES, user=request.user)
        
        if form.is_valid():
            ticket = form.save()
            
            AuditLog.objects.create(
                ticket=ticket,
                user=request.user,
                action='CREATE',
                new_value=f"Ticket créé avec la priorité {ticket.get_priority_display()}"
            )
            
            # Notification : Ticket créé
            from .notifications import NotificationService
            NotificationService.notify_ticket_created(ticket)
            
            messages.success(
                request,
                _(f'Ticket #{ticket.reference} créé avec succès!')
            )
            
            return redirect('tickets:detail', pk=ticket.id)
    else:
        form = TicketCreateForm(user=request.user)
    
    context = {
        'form': form,
        'is_edit': False,
    }
    
    return render(request, 'tickets/create.html', context)


# ============================================================
# DÉTAIL D'UN TICKET
# ============================================================

@login_required
def ticket_detail(request, pk):
    """
    Détail d'un ticket avec commentaires, pièces jointes,
    assignation par manager et export PDF
    """
    ticket = get_object_or_404(
        Ticket.objects.select_related('created_by', 'assigned_to')
        .prefetch_related('comments__user', 'attachments', 'audit_logs__user'),
        pk=pk
    )
    
    # Vérifier les permissions
    if not request.user.is_admin and not request.user.is_manager:
        if not request.user.is_technician:
            if ticket.created_by != request.user and ticket.assigned_to != request.user:
                messages.error(request, _('Vous n\'avez pas accès à ce ticket.'))
                return redirect('tickets:list')
    
    # Formulaire de commentaire
    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.ticket = ticket
            comment.user = request.user
            comment.save()
            
            AuditLog.objects.create(
                ticket=ticket,
                user=request.user,
                action='COMMENT',
                new_value=f"Nouveau commentaire: {comment.content[:50]}..."
            )
            
            # Notification
            from .notifications import NotificationService
            NotificationService.notify_comment_added(comment)
            
            messages.success(request, _('Commentaire ajouté avec succès!'))
            return redirect('tickets:detail', pk=ticket.id)
    else:
        comment_form = CommentForm()
    
    # Formulaire de changement de statut
    status_form = TicketStatusForm(initial={'status': ticket.status})
    
    # Vérifications des permissions
    can_change_status = (
        request.user.is_admin or
        request.user.is_manager or
        (request.user.is_technician and ticket.assigned_to == request.user)
    )
    
    # ✅ Manager ou Admin peut assigner
    can_assign = request.user.is_admin or request.user.is_manager
    
    # ✅ Vérifier si le ticket peut être exporté
    can_export = request.user.is_admin or request.user.is_manager or ticket.created_by == request.user
    
    # Liste des techniciens pour l'assignation
    technicians = User.objects.filter(
        is_staff=True,
        is_active=True
    ).order_by('username')
    
    # ✅ Tickets non assignés pour le manager
    unassigned_tickets = Ticket.objects.filter(
        assigned_to__isnull=True,
        status='OPEN'
    ).order_by('-priority', '-created_at')
    
    context = {
        'ticket': ticket,
        'comment_form': comment_form,
        'status_form': status_form,
        'can_change_status': can_change_status,
        'can_assign': can_assign,
        'can_export': can_export,
        'is_technician': request.user.is_technician,
        'is_admin': request.user.is_admin,
        'is_manager': request.user.is_manager,
        'comments': ticket.comments.all().order_by('created_at'),
        'attachments': ticket.attachments.all(),
        'audit_logs': ticket.audit_logs.all().order_by('-created_at')[:20],
        'technicians': technicians,
        'unassigned_tickets': unassigned_tickets,  # ✅ Pour le dashboard manager
    }
    
    return render(request, 'tickets/detail.html', context)

# ============================================================
# PRENDRE UN TICKET (Technicien)
# ============================================================

@login_required
@require_POST
def ticket_take(request, pk):
    """
    Un technicien prend un ticket
    """
    ticket = get_object_or_404(Ticket, pk=pk)
    
    if not request.user.is_staff:
        messages.error(request, 'Vous n\'avez pas la permission de prendre ce ticket.')
        return redirect('tickets:detail', pk=ticket.id)
    
    if ticket.assigned_to:
        messages.warning(request, f'Ce ticket est déjà assigné à {ticket.assigned_to.username}')
        return redirect('tickets:detail', pk=ticket.id)
    
    ticket.assigned_to = request.user
    ticket.status = 'IN_PROGRESS'
    ticket.save()
    
    AuditLog.objects.create(
        ticket=ticket,
        user=request.user,
        action='ASSIGN',
        new_value=f"Assigné à {request.user.username}"
    )
    
    # Notification
    from .notifications import NotificationService
    NotificationService.notify_ticket_taken(ticket, request.user)
    
    messages.success(request, f'Vous avez pris le ticket #{ticket.reference}!')
    return redirect('tickets:detail', pk=ticket.id)


# ============================================================
# ASSIGNER UN TICKET (Manager/Admin)
# ============================================================

@login_required
@require_POST
def ticket_assign(request, pk):
    """
    Assignation d'un ticket à un technicien par un Manager ou Admin
    """
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Vérifier que l'utilisateur est Manager ou Admin
    if not (request.user.is_admin or request.user.is_manager):
        messages.error(request, 'Vous n\'avez pas la permission d\'assigner des tickets.')
        return redirect('tickets:detail', pk=ticket.id)
    
    # Vérifier que le ticket n'est pas déjà assigné
    if ticket.assigned_to:
        messages.warning(
            request,
            f'Ce ticket est déjà assigné à {ticket.assigned_to.get_full_name() or ticket.assigned_to.username}'
        )
        return redirect('tickets:detail', pk=ticket.id)
    
    technician_id = request.POST.get('technician_id')
    
    if not technician_id:
        messages.error(request, 'Veuillez sélectionner un technicien.')
        return redirect('tickets:detail', pk=ticket.id)
    
    try:
        technician = User.objects.get(pk=technician_id, is_staff=True)
        
        old_assigned_to = ticket.assigned_to
        ticket.assigned_to = technician
        ticket.status = 'IN_PROGRESS'
        ticket.save()
        
        AuditLog.objects.create(
            ticket=ticket,
            user=request.user,
            action='ASSIGN',
            old_value=str(old_assigned_to) if old_assigned_to else 'Non assigné',
            new_value=str(technician)
        )
        
        # Notification
        from .notifications import NotificationService
        NotificationService.notify_assigned(ticket, request.user)
        
        messages.success(
            request,
            _(f'Ticket #{ticket.reference} assigné à {technician.get_full_name()} avec succès!')
        )
        
    except User.DoesNotExist:
        messages.error(request, _('Technicien non trouvé.'))
    
    return redirect('tickets:detail', pk=ticket.id)


# ============================================================
# DÉSASSIGNER UN TICKET
# ============================================================

@login_required
@require_POST
def ticket_unassign(request, pk):
    """
    Désassignation d'un ticket
    """
    ticket = get_object_or_404(Ticket, pk=pk)
    
    if ticket.assigned_to != request.user and not (request.user.is_admin or request.user.is_manager):
        messages.error(request, 'Vous n\'avez pas la permission de désassigner ce ticket.')
        return redirect('tickets:detail', pk=ticket.id)
    
    old_assigned_to = ticket.assigned_to
    ticket.assigned_to = None
    ticket.status = 'OPEN'
    ticket.save()
    
    AuditLog.objects.create(
        ticket=ticket,
        user=request.user,
        action='ASSIGN',
        old_value=str(old_assigned_to) if old_assigned_to else 'Non assigné',
        new_value='Désassigné'
    )
    
    messages.success(request, f'Ticket #{ticket.reference} désassigné avec succès!')
    return redirect('tickets:detail', pk=ticket.id)


# ============================================================
# CHANGER LE STATUT
# ============================================================

@login_required
@require_POST
def ticket_change_status(request, pk):
    """
    Changement de statut d'un ticket
    """
    ticket = get_object_or_404(Ticket, pk=pk)
    
    if not request.user.is_admin and not request.user.is_manager:
        if not (request.user.is_technician and ticket.assigned_to == request.user):
            messages.error(request, 'Vous n\'avez pas la permission de changer le statut.')
            return redirect('tickets:detail', pk=ticket.id)
    
    status_form = TicketStatusForm(request.POST)
    
    if status_form.is_valid():
        new_status = status_form.cleaned_data['status']
        comment = status_form.cleaned_data.get('comment', '')
        
        try:
            old_status = ticket.status
            ticket.change_status(new_status, request.user, comment)
            
            # Notification
            from .notifications import NotificationService
            NotificationService.notify_status_changed(ticket, old_status, request.user)
            
            messages.success(
                request,
                _(f'Statut du ticket #{ticket.reference} changé avec succès!')
            )
            
        except ValueError as e:
            messages.error(request, str(e))
    else:
        messages.error(request, _('Formulaire invalide.'))
    
    return redirect('tickets:detail', pk=ticket.id)


# ============================================================
# ÉDITER UN TICKET
# ============================================================

@login_required
@permission_required('tickets.can_assign_tickets', raise_exception=True)
def ticket_edit(request, pk):
    """
    Édition d'un ticket (admin/technicien)
    """
    ticket = get_object_or_404(Ticket, pk=pk)
    
    if request.method == 'POST':
        form = TicketEditForm(request.POST, instance=ticket)
        
        if form.is_valid():
            old_assigned_to = ticket.assigned_to
            old_status = ticket.status
            
            ticket = form.save()
            
            changes = []
            if old_assigned_to != ticket.assigned_to:
                changes.append(
                    f"Assignation changée: {old_assigned_to} -> {ticket.assigned_to}"
                )
            if old_status != ticket.status:
                changes.append(
                    f"Statut changé: {old_status} -> {ticket.status}"
                )
            
            if changes:
                AuditLog.objects.create(
                    ticket=ticket,
                    user=request.user,
                    action='UPDATE',
                    old_value=old_assigned_to,
                    new_value=ticket.assigned_to,
                    field_name=', '.join(changes)
                )
            
            messages.success(
                request,
                _(f'Ticket #{ticket.reference} modifié avec succès!')
            )
            
            return redirect('tickets:detail', pk=ticket.id)
    else:
        form = TicketEditForm(instance=ticket)
    
    context = {
        'form': form,
        'ticket': ticket,
        'is_edit': True,
    }
    
    return render(request, 'tickets/create.html', context)


# ============================================================
# SUPPRIMER UN TICKET
# ============================================================

@login_required
@require_POST
def ticket_delete(request, pk):
    """
    Suppression d'un ticket (admin seulement)
    """
    if not request.user.is_admin:
        messages.error(request, _('Vous n\'avez pas la permission de supprimer des tickets.'))
        return redirect('tickets:list')
    
    ticket = get_object_or_404(Ticket, pk=pk)
    reference = ticket.reference
    
    for attachment in ticket.attachments.all():
        attachment.file.delete(save=False)
    
    ticket.delete()
    
    messages.success(request, _(f'Ticket #{reference} supprimé avec succès!'))
    return redirect('tickets:list')


# ============================================================
# COMMENTAIRES
# ============================================================

@login_required
@require_POST
def comment_delete(request, pk):
    """
    Suppression d'un commentaire
    """
    comment = get_object_or_404(Comment, pk=pk)
    
    if not (comment.user == request.user or request.user.is_admin):
        messages.error(request, _('Vous n\'avez pas la permission de supprimer ce commentaire.'))
        return redirect('tickets:detail', pk=comment.ticket.id)
    
    ticket_id = comment.ticket.id
    comment.delete()
    
    messages.success(request, _('Commentaire supprimé avec succès.'))
    return redirect('tickets:detail', pk=ticket_id)


@login_required
@require_POST
def comment_edit(request, pk):
    """
    Édition d'un commentaire
    """
    comment = get_object_or_404(Comment, pk=pk)
    
    if not (comment.user == request.user or request.user.is_admin):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    content = request.POST.get('content')
    if not content:
        return JsonResponse({'error': 'Contenu vide'}, status=400)
    
    comment.content = content
    comment.save()
    
    return JsonResponse({
        'success': True,
        'content': content
    })


# ============================================================
# EXPORT CSV
# ============================================================

@login_required
@require_GET
def ticket_export(request):
    """
    Export des tickets en CSV
    """
    if not request.user.is_admin and not request.user.is_manager:
        messages.error(request, _('Vous n\'avez pas la permission d\'exporter les tickets.'))
        return redirect('tickets:list')
    
    tickets = Ticket.objects.select_related('created_by', 'assigned_to')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="tickets_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Référence', 'Titre', 'Catégorie', 'Priorité', 'Statut',
        'Créé par', 'Assigné à', 'Créé le', 'Résolu le'
    ])
    
    for ticket in tickets:
        writer.writerow([
            ticket.reference,
            ticket.title,
            ticket.get_category_display(),
            ticket.get_priority_display(),
            ticket.get_status_display(),
            ticket.created_by.get_full_name(),
            ticket.assigned_to.get_full_name() if ticket.assigned_to else '',
            ticket.created_at.strftime('%d/%m/%Y %H:%M'),
            ticket.resolved_at.strftime('%d/%m/%Y %H:%M') if ticket.resolved_at else '',
        ])
    
    return response


# ============================================================
# DASHBOARD PRINCIPAL (REDIRECTION SELON RÔLE)
# ============================================================

@login_required
def dashboard_view(request):
    """
    Redirige vers le bon dashboard selon le rôle
    """
    if request.user.is_superuser or request.user.is_admin or request.user.is_manager:
        return dashboard_manager(request)
    elif request.user.is_technician:
        return dashboard_technician(request)
    else:
        return dashboard_employee(request)


# ============================================================
# DASHBOARD MANAGER
# ============================================================

@login_required
def dashboard_manager(request):
    """
    Tableau de bord Manager avec toutes les statistiques
    """
    if not (request.user.is_staff or request.user.is_manager or request.user.is_admin):
        messages.error(request, 'Vous n\'avez pas accès à ce tableau de bord.')
        return redirect('tickets:list')
    
    # Récupérer toutes les statistiques
    stats = DashboardService.get_manager_stats()
    technician_performance = DashboardService.get_technician_performance()
    recent_tickets = DashboardService.get_recent_tickets()
    urgent_tickets = DashboardService.get_urgent_tickets()
    sla_stats = DashboardService.get_sla_stats()
    
    # Techniciens et tickets non assignés
    technicians = User.objects.filter(is_staff=True, is_active=True)
    unassigned_tickets = Ticket.objects.filter(assigned_to__isnull=True, status='OPEN')
    
    context = {
        'stats': stats,
        'technician_performance': technician_performance,
        'recent_tickets': recent_tickets,
        'urgent_tickets': urgent_tickets,
        'sla_stats': sla_stats,
        'technicians': technicians,
        'unassigned_tickets': unassigned_tickets,
        'is_manager': True,
    }
    
    return render(request, 'tickets/dashboard_manager.html', context)


# ============================================================
# DASHBOARD TECHNICIEN
# ============================================================

@login_required
def dashboard_technician(request):
    """
    Tableau de bord Technicien
    """
    if not request.user.is_staff:
        messages.error(request, 'Vous n\'avez pas accès à ce tableau de bord.')
        return redirect('tickets:list')
    
    my_tickets = Ticket.objects.filter(assigned_to=request.user)
    
    available_tickets = Ticket.objects.filter(
        assigned_to__isnull=True,
        status='OPEN'
    ).order_by('-priority', '-created_at')
    
    stats = {
        'total': my_tickets.count(),
        'in_progress': my_tickets.filter(status='IN_PROGRESS').count(),
        'resolved': my_tickets.filter(status='RESOLVED').count(),
        'open': my_tickets.filter(status='OPEN').count(),
    }
    
    context = {
        'my_tickets': my_tickets,
        'available_tickets': available_tickets,
        'stats': stats,
        'is_technician': True,
    }
    
    return render(request, 'tickets/dashboard_technician.html', context)


# ============================================================
# DASHBOARD EMPLOYÉ
# ============================================================

@login_required
def dashboard_employee(request):
    """
    Tableau de bord Employé
    """
    my_tickets = Ticket.objects.filter(created_by=request.user)
    
    stats = {
        'total': my_tickets.count(),
        'open': my_tickets.filter(status='OPEN').count(),
        'in_progress': my_tickets.filter(status='IN_PROGRESS').count(),
        'resolved': my_tickets.filter(status='RESOLVED').count(),
        'closed': my_tickets.filter(status='CLOSED').count(),
    }
    
    context = {
        'my_tickets': my_tickets,
        'stats': stats,
    }
    
    return render(request, 'tickets/dashboard_employee.html', context)


# ============================================================
# KANBAN
# ============================================================

@login_required
def ticket_kanban_view(request):
    """
    Vue Kanban des tickets (Drag & Drop)
    """
    tickets_by_status = {}
    for status in Ticket.Status.choices:
        status_value = status[0]
        tickets = Ticket.objects.filter(status=status_value).select_related(
            'created_by', 'assigned_to'
        ).order_by('-priority', 'created_at')
        tickets_by_status[status_value] = tickets[:20]
    
    context = {
        'tickets_by_status': tickets_by_status,
        'is_technician': request.user.is_technician,
        'is_admin': request.user.is_admin,
    }
    
    return render(request, 'tickets/kanban.html', context)


@login_required
@require_POST
def ticket_drag_drop(request, pk):
    """
    API pour le Drag & Drop (changement de statut)
    """
    ticket = get_object_or_404(Ticket, pk=pk)
    new_status = request.POST.get('status')
    
    if not request.user.is_admin and not request.user.is_manager:
        if not (request.user.is_technician and ticket.assigned_to == request.user):
            return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        ticket.change_status(new_status, request.user)
        return JsonResponse({'success': True})
    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)


# ============================================================
# API JSON (AJAX)
# ============================================================

@login_required
@require_GET
def technician_list_json(request):
    """
    Liste des techniciens en JSON (pour les appels AJAX)
    """
    technicians = User.objects.filter(
        is_staff=True,
        is_active=True
    ).annotate(
        active_count=Count('assigned_tickets', filter=Q(
            assigned_tickets__status__in=['OPEN', 'IN_PROGRESS']
        ))
    ).order_by('active_count')
    
    data = [{
        'id': str(tech.id),
        'name': tech.get_full_name() or tech.username,
        'active_count': tech.active_count,
        'is_available': getattr(tech, 'is_available', True),
    } for tech in technicians]
    
    return JsonResponse(data, safe=False)


@login_required
@require_GET
def dashboard_stats_json(request):
    """
    API JSON pour les données du dashboard (mise à jour en temps réel)
    """
    period = request.GET.get('period', 'week')
    
    data = {
        'stats': DashboardService.get_manager_stats(),
        'technician_performance': DashboardService.get_technician_performance(),
        'sla_stats': DashboardService.get_sla_stats(),
    }
    
    return JsonResponse(data)


# ============================================================
# NOTIFICATIONS API (AJAX)
# ============================================================

@login_required
def get_notifications(request):
    """
    API pour récupérer les notifications (AJAX)
    """
    from .notifications import NotificationService
    
    notifications = NotificationService.get_notifications(request.user)
    unread_count = NotificationService.get_unread_count(request.user)
    
    data = {
        'unread_count': unread_count,
        'notifications': [
            {
                'id': str(n.id),
                'type': n.get_type_display(),
                'message': n.message,
                'is_read': n.is_read,
                'created_at': n.created_at.strftime('%d/%m/%Y %H:%M'),
                'link': n.link,
            }
            for n in notifications
        ]
    }
    return JsonResponse(data)


@login_required
@require_POST
def mark_notification_read(request, pk):
    """
    Marquer une notification comme lue
    """
    from .models import Notification
    
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.mark_as_read()
    return JsonResponse({'success': True})


# ============================================================
# ASSIGNER UN TICKET DEPUIS LE DASHBOARD
# ============================================================

@login_required
@require_POST
def ticket_assign_from_dashboard(request):
    """
    Assigner un ticket depuis le dashboard (POST avec ticket_id)
    """
    if not (request.user.is_superuser or request.user.role == 'MANAGER'):
        messages.error(request, 'Vous n\'avez pas la permission d\'assigner des tickets.')
        return redirect('tickets:dashboard')
    
    ticket_id = request.POST.get('ticket_id')
    technician_id = request.POST.get('technician_id')
    
    if not ticket_id:
        messages.error(request, 'Veuillez sélectionner un ticket.')
        return redirect('tickets:dashboard')
    
    if not technician_id:
        messages.error(request, 'Veuillez sélectionner un technicien.')
        return redirect('tickets:dashboard')
    
    try:
        ticket = Ticket.objects.get(id=ticket_id)
        technician = User.objects.get(id=technician_id, is_staff=True)
        
        if ticket.assigned_to:
            messages.warning(request, f'Le ticket {ticket.reference} est déjà assigné.')
            return redirect('tickets:dashboard')
        
        ticket.assigned_to = technician
        ticket.status = 'IN_PROGRESS'
        ticket.save()
        
        from .notifications import NotificationService
        NotificationService.notify_assigned(ticket, request.user)
        
        messages.success(request, f'Ticket {ticket.reference} assigné à {technician.get_full_name()}')
        
    except Ticket.DoesNotExist:
        messages.error(request, 'Ticket non trouvé.')
    except User.DoesNotExist:
        messages.error(request, 'Technicien non trouvé.')
    
    return redirect('tickets:dashboard')


# ============================================================
# ACTIONS EN MASSE
# ============================================================

@login_required
@require_POST
def ticket_bulk_action(request):
    """
    Actions en masse sur les tickets
    """
    if not request.user.is_admin and not request.user.is_manager:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    ticket_ids = request.POST.getlist('ticket_ids')
    action = request.POST.get('action')
    
    if not ticket_ids:
        messages.error(request, _('Veuillez sélectionner au moins un ticket.'))
        return redirect('tickets:list')
    
    tickets = Ticket.objects.filter(id__in=ticket_ids)
    
    if action == 'assign':
        technician_id = request.POST.get('technician_id')
        try:
            technician = User.objects.get(id=technician_id)
            for ticket in tickets:
                ticket.assigned_to = technician
                ticket.status = 'IN_PROGRESS'
                ticket.save()
            messages.success(request, _(f'{tickets.count()} tickets assignés à {technician.get_full_name()}'))
        except User.DoesNotExist:
            messages.error(request, _('Technicien non trouvé.'))
    
    elif action == 'status':
        new_status = request.POST.get('status')
        for ticket in tickets:
            ticket.status = new_status
            if new_status == 'RESOLVED' and not ticket.resolved_at:
                ticket.resolved_at = timezone.now()
            ticket.save()
        messages.success(request, _(f'{tickets.count()} tickets mis à jour.'))
    
    elif action == 'delete':
        if request.user.is_admin:
            count = tickets.count()
            tickets.delete()
            messages.success(request, _(f'{count} tickets supprimés.'))
        else:
            messages.error(request, _('Vous n\'avez pas la permission de supprimer des tickets.'))
    
    return redirect('tickets:list')



# apps/tickets/views.py - Ajouter ces fonctions

@login_required
def ticket_export_single_pdf(request, pk):
    """
    Export d'un seul ticket en PDF (Manager, Admin, ou propriétaire du ticket)
    """
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Vérifier les permissions
    if not (request.user.is_admin or request.user.is_manager or ticket.created_by == request.user):
        messages.error(request, 'Vous n\'avez pas la permission d\'exporter ce ticket.')
        return redirect('tickets:list')
    
    # Récupérer les commentaires et l'historique
    comments = ticket.comments.all().order_by('created_at')
    audit_logs = ticket.audit_logs.all().order_by('created_at')
    
    context = {
        'ticket': ticket,
        'comments': comments,
        'audit_logs': audit_logs,
        'user': request.user,
        'date': datetime.now(),
    }
    
    # Rendre le template HTML
    template = get_template('tickets/export_single_pdf.html')
    html = template.render(context)
    
    return HttpResponse(html, content_type='text/html')


@login_required
def ticket_export_all_pdf(request):
    """
    Export de tous les tickets en PDF (avec filtres)
    """
    if not request.user.is_admin and not request.user.is_manager:
        messages.error(request, 'Vous n\'avez pas la permission d\'exporter tous les tickets.')
        return redirect('tickets:list')
    
    # Récupérer les tickets avec les filtres
    tickets = Ticket.objects.select_related('created_by', 'assigned_to').order_by('-created_at')
    
    # Appliquer les filtres de recherche
    search_form = TicketSearchForm(request.GET)
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search')
        if search_query:
            tickets = tickets.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(reference__icontains=search_query)
            )
        
        status = search_form.cleaned_data.get('status')
        if status:
            tickets = tickets.filter(status=status)
        
        priority = search_form.cleaned_data.get('priority')
        if priority:
            tickets = tickets.filter(priority=priority)
        
        category = search_form.cleaned_data.get('category')
        if category:
            tickets = tickets.filter(category=category)
        
        assigned_to = search_form.cleaned_data.get('assigned_to')
        if assigned_to:
            tickets = tickets.filter(assigned_to_id=assigned_to)
        
        date_from = search_form.cleaned_data.get('date_from')
        if date_from:
            tickets = tickets.filter(created_at__date__gte=date_from)
        
        date_to = search_form.cleaned_data.get('date_to')
        if date_to:
            tickets = tickets.filter(created_at__date__lte=date_to)
    
    context = {
        'tickets': tickets,
        'user': request.user,
        'date': datetime.now(),
        'total': tickets.count(),
        'status_filter': request.GET.get('status', 'Tous'),
        'priority_filter': request.GET.get('priority', 'Toutes'),
    }
    
    template = get_template('tickets/export_all_pdf.html')
    html = template.render(context)
    
    return HttpResponse(html, content_type='text/html')

@login_required
def report_view(request):
    """
    Page de génération de rapports (Manager/Admin uniquement)
    """
    if not (request.user.is_admin or request.user.is_manager):
        messages.error(request, 'Vous n\'avez pas accès à cette page.')
        return redirect('tickets:dashboard')
    
    # Récupérer les techniciens pour le filtre
    technicians = User.objects.filter(is_staff=True, is_active=True)
    
    context = {
        'technicians': technicians,
        'today': timezone.now().date(),
        'last_month': timezone.now().date() - timedelta(days=30),
    }
    
    return render(request, 'tickets/report.html', context)


@login_required
def report_generate(request):
    """
    Génère un rapport de performance (Manager/Admin uniquement)
    """
    if not (request.user.is_admin or request.user.is_manager):
        messages.error(request, 'Vous n\'avez pas accès à cette page.')
        return redirect('tickets:dashboard')
    
    # Récupérer les paramètres
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    technician_id = request.GET.get('technician_id')
    format_type = request.GET.get('format', 'html')
    
    # Convertir les dates
    start_date = None
    end_date = None
    
    if start_date_str:
        try:
            start_date = timezone.make_aware(
                datetime.strptime(start_date_str, '%Y-%m-%d')
            )
        except ValueError:
            pass
    
    if end_date_str:
        try:
            end_date = timezone.make_aware(
                datetime.strptime(end_date_str, '%Y-%m-%d')
            )
        except ValueError:
            pass
    
    # Récupérer les données
    data = DashboardService.get_report_data(start_date, end_date, technician_id)
    
    # Ajouter les informations du technicien
    technician_name = 'Tous les techniciens'
    if technician_id:
        try:
            tech = User.objects.get(id=technician_id)
            technician_name = tech.get_full_name() or tech.username
        except User.DoesNotExist:
            pass
    
    data['technician_name'] = technician_name
    data['generated_at'] = datetime.now()
    
    context = {
        'data': data,
        'user': request.user,
        'format': format_type,
    }
    
    # Rendre le template
    template = get_template('tickets/report_performance.html')
    html = template.render(context)
    
    # Format PDF (via HTML)
    if format_type == 'pdf':
        return HttpResponse(html, content_type='text/html')
    elif format_type == 'csv':
        return generate_report_csv(data)
    else:  # HTML
        return HttpResponse(html, content_type='text/html')


def generate_report_csv(data):
    """
    Génère un rapport au format CSV
    """
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="rapport_performance.csv"'
    
    writer = csv.writer(response)
    
    # En-tête
    writer.writerow(['RAPPORT DE PERFORMANCE'])
    writer.writerow([f"Période: {data['period']['start']} - {data['period']['end']}"])
    writer.writerow([])
    
    # Résumé
    writer.writerow(['RÉSUMÉ GLOBAL'])
    writer.writerow(['Total tickets', data['summary']['total']])
    writer.writerow(['Résolus', data['summary']['resolved']])
    writer.writerow(['Taux de résolution', f"{data['summary']['resolution_rate']}%"])
    writer.writerow(['Temps moyen', f"{data['summary']['avg_resolution_hours']}h"])
    writer.writerow(['Conformité SLA', f"{data['summary']['sla_rate']}%"])
    writer.writerow([])
    
    # Performance des techniciens
    writer.writerow(['PERFORMANCE DES TECHNICIENS'])
    writer.writerow(['Nom', 'Assignés', 'Résolus', 'Taux', 'Temps moyen', 'Satisfaction', 'Score'])
    for tech in data['technician_performance']:
        writer.writerow([
            tech['name'],
            tech['total_assigned'],
            tech['total_resolved'],
            f"{tech['resolution_rate']}%",
            f"{tech['avg_resolution_hours']}h" if tech['avg_resolution_hours'] else '-',
            f"{tech['satisfaction_rate']}%",
            f"{tech['performance_score']}%"
        ])
    
    return response

# apps/tickets/views.py - Ajouter cette fonction

@login_required
def ticket_assign_mass(request):
    """
    Assignation en masse de tickets (Manager/Admin uniquement)
    """
    if not (request.user.is_admin or request.user.is_manager):
        messages.error(request, 'Vous n\'avez pas accès à cette page.')
        return redirect('tickets:list')
    
    if request.method == 'POST':
        ticket_ids = request.POST.getlist('ticket_ids')
        technician_id = request.POST.get('technician_id')
        
        if not ticket_ids:
            messages.error(request, 'Veuillez sélectionner au moins un ticket.')
            return redirect('tickets:assign_mass')
        
        if not technician_id:
            messages.error(request, 'Veuillez sélectionner un technicien.')
            return redirect('tickets:assign_mass')
        
        try:
            technician = User.objects.get(id=technician_id, is_staff=True)
            tickets = Ticket.objects.filter(id__in=ticket_ids)
            
            count = 0
            for ticket in tickets:
                if not ticket.assigned_to:
                    ticket.assigned_to = technician
                    ticket.status = 'IN_PROGRESS'
                    ticket.save()
                    count += 1
                    
                    # Notification
                    from .services import NotificationService
                    NotificationService.notify_assigned(ticket, request.user)
            
            messages.success(request, f'{count} tickets assignés à {technician.get_full_name()} avec succès!')
            
        except User.DoesNotExist:
            messages.error(request, 'Technicien non trouvé.')
        
        return redirect('tickets:list')
    
    # GET : Afficher le formulaire
    technicians = User.objects.filter(is_staff=True, is_active=True)
    unassigned_tickets = Ticket.objects.filter(assigned_to__isnull=True, status='OPEN')
    
    context = {
        'technicians': technicians,
        'unassigned_tickets': unassigned_tickets,
    }
    
    return render(request, 'tickets/assign_mass.html', context)

@login_required
def stats_advanced(request):
    """
    Statistiques avancées avec graphiques (Manager/Admin uniquement)
    """
    if not (request.user.is_admin or request.user.is_manager):
        messages.error(request, 'Vous n\'avez pas accès à cette page.')
        return redirect('tickets:dashboard')
    
    period = request.GET.get('period', 'month')
    
    # Récupérer les données
    stats = DashboardService.get_advanced_stats(period)
    
    # Préparer les données pour les graphiques Chart.js
    chart_data = {
        'daily_dates': [d['date'] for d in stats['daily_evolution']],
        'daily_created': [d['created'] for d in stats['daily_evolution']],
        'daily_resolved': [d['resolved'] for d in stats['daily_evolution']],
        'categories': {
            'labels': list(stats['categories'].keys()),
            'values': list(stats['categories'].values()),
        },
        'priorities': {
            'labels': list(stats['priorities'].keys()),
            'values': list(stats['priorities'].values()),
        },
        'technicians': {
            'labels': [t['name'] for t in stats['technicians']],
            'scores': [t['score'] for t in stats['technicians']],
            'rates': [t['rate'] for t in stats['technicians']],
        }
    }
    
    context = {
        'stats': stats,
        'chart_data': chart_data,
        'period': period,
        'periods': ['week', 'month', 'year'],
        'is_manager': request.user.is_manager,
        'is_admin': request.user.is_admin,
    }
    
    return render(request, 'tickets/stats_advanced.html', context)

# apps/tickets/views.py

@login_required
@require_POST
def ticket_assign_by_manager(request, pk):
    """
    Assigner un ticket à un technicien (Manager/Admin uniquement)
    """
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Vérifier que l'utilisateur est Manager ou Admin
    if not (request.user.is_admin or request.user.is_manager):
        messages.error(request, 'Vous n\'avez pas la permission d\'assigner des tickets.')
        return redirect('tickets:detail', pk=ticket.id)
    
    # Vérifier que le ticket n'est pas déjà assigné
    if ticket.assigned_to:
        messages.warning(request, f'Ce ticket est déjà assigné à {ticket.assigned_to.get_full_name() or ticket.assigned_to.username}')
        return redirect('tickets:detail', pk=ticket.id)
    
    technician_id = request.POST.get('technician_id')
    
    if not technician_id:
        messages.error(request, 'Veuillez sélectionner un technicien.')
        return redirect('tickets:detail', pk=ticket.id)
    
    try:
        technician = User.objects.get(pk=technician_id, is_staff=True)
        
        ticket.assigned_to = technician
        ticket.status = 'IN_PROGRESS'
        ticket.save()
        
        # Audit log
        AuditLog.objects.create(
            ticket=ticket,
            user=request.user,
            action='ASSIGN',
            old_value='Non assigné',
            new_value=str(technician)
        )
        
        # Notification
        from .notifications import NotificationService
        NotificationService.notify_assigned(ticket, request.user)
        
        messages.success(
            request,
            f'Ticket #{ticket.reference} assigné à {technician.get_full_name() or technician.username} avec succès!'
        )
        
    except User.DoesNotExist:
        messages.error(request, 'Technicien non trouvé.')
    
    return redirect('tickets:detail', pk=ticket.id)