# apps/users/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django.core.exceptions import ValidationError

from .forms import CustomUserCreationForm, UserProfileForm, CustomUserChangeForm, RoleLoginForm
from .models import User
from apps.tickets.models import Ticket
from .forms import RoleLoginForm
from django.contrib.auth import login, logout


User = get_user_model()


# ============================================================
# CONNEXION AVEC SÉLECTION DE RÔLE
# ============================================================

def login_view(request):
    """
    Vue de connexion personnalisée avec sélection de rôle
    """
    # Si l'utilisateur est déjà connecté, rediriger vers le dashboard
    if request.user.is_authenticated:
        return redirect('tickets:dashboard')
    
    if request.method == 'POST':
        form = RoleLoginForm(request, data=request.POST)
        
        if form.is_valid():
            # Récupérer l'utilisateur
            user = form.user_cache
            
            # Se souvenir de moi
            remember_me = form.cleaned_data.get('remember_me')
            if not remember_me:
                request.session.set_expiry(0)  # Expire à la fermeture du navigateur
            else:
                request.session.set_expiry(1209600)  # 2 semaines
            
            # Connecter l'utilisateur
            login(request, user)
            
            messages.success(request, f'Bienvenue {user.get_full_name() or user.username} !')
            
            # Rediriger vers la page demandée ou le dashboard
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            
            return redirect('tickets:dashboard')
        else:
            # Afficher les erreurs du formulaire
            for error in form.non_field_errors():
                messages.error(request, error)
    
    else:
        form = RoleLoginForm()
    
    context = {
        'form': form,
        'page_title': 'Connexion - Helpdesk',
    }
    
    return render(request, 'users/login.html', context)


# ============================================================
# DÉCONNEXION
# ============================================================

def logout_view(request):
    """
    Vue de déconnexion
    """
    logout(request)
    messages.info(request, _('Vous avez été déconnecté.'))
    return redirect('login')


# ============================================================
# PROFIL UTILISATEUR
# ============================================================

@login_required
def profile_view(request):
    """
    Vue du profil utilisateur
    """
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            user = form.save()
            messages.success(request, _('Votre profil a été mis à jour.'))
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    # Statistiques de l'utilisateur
    if request.user.is_technician:
        stats = {
            'assigned_count': request.user.get_assigned_tickets_count(),
            'resolved_today': request.user.get_resolved_tickets_count('today'),
            'avg_resolution_time': request.user.get_average_resolution_time(),
        }
    else:
        created_tickets = Ticket.objects.filter(created_by=request.user)
        stats = {
            'total_created': created_tickets.count(),
            'open_tickets': created_tickets.filter(status='OPEN').count(),
            'resolved_tickets': created_tickets.filter(status='RESOLVED').count(),
        }
    
    context = {
        'form': form,
        'stats': stats,
    }
    return render(request, 'users/profile.html', context)


# ============================================================
# CHANGEMENT DE MOT DE PASSE
# ============================================================

@login_required
def change_password_view(request):
    """
    Vue de changement de mot de passe
    """
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
        if not request.user.check_password(old_password):
            messages.error(request, _('Mot de passe actuel incorrect.'))
            return redirect('change_password')
        
        if new_password1 != new_password2:
            messages.error(request, _('Les mots de passe ne correspondent pas.'))
            return redirect('change_password')
        
        if len(new_password1) < 8:
            messages.error(request, _('Le mot de passe doit faire au moins 8 caractères.'))
            return redirect('change_password')
        
        request.user.set_password(new_password1)
        request.user.save()
        update_session_auth_hash(request, request.user)
        messages.success(request, _('Votre mot de passe a été modifié.'))
        return redirect('profile')
    
    return render(request, 'users/change_password.html')


# ============================================================
# INSCRIPTION
# ============================================================

class RegisterView(CreateView):
    """
    Vue d'inscription
    """
    model = User
    form_class = CustomUserCreationForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('login')
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Inscription réussie! Vous pouvez maintenant vous connecter.'))
        return response


# ============================================================
# GESTION DES UTILISATEURS (ADMIN)
# ============================================================

@login_required
def user_list_view(request):
    """
    Liste des utilisateurs (admin)
    """
    if not request.user.is_admin:
        messages.error(request, _('Vous n\'avez pas les permissions nécessaires.'))
        return redirect('dashboard')
    
    users = User.objects.all().order_by('-date_joined')
    context = {'users': users}
    return render(request, 'users/user_list.html', context)


@login_required
def user_edit_view(request, pk):
    """
    Modification d'un utilisateur (admin)
    """
    if not request.user.is_admin:
        messages.error(request, _('Vous n\'avez pas les permissions nécessaires.'))
        return redirect('dashboard')
    
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, _(f'L\'utilisateur {user.username} a été modifié.'))
            return redirect('user_list')
    else:
        form = CustomUserChangeForm(instance=user)
    
    context = {
        'form': form,
        'user_edit': user,
    }
    return render(request, 'users/user_edit.html', context)


@login_required
def user_delete_view(request, pk):
    """
    Suppression d'un utilisateur (admin)
    """
    if not request.user.is_admin:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    user = get_object_or_404(User, pk=pk)
    
    if request.user == user:
        return JsonResponse({'error': 'Vous ne pouvez pas vous supprimer vous-même.'}, status=400)
    
    user.delete()
    messages.success(request, _(f'L\'utilisateur a été supprimé.'))
    return redirect('user_list')


# ============================================================
# RÉINITIALISATION DU MOT DE PASSE
# ============================================================

class CustomPasswordResetView(PasswordResetView):
    """
    Vue de réinitialisation de mot de passe personnalisée
    """
    template_name = 'registration/password_reset_form.html'
    email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'registration/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'registration/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'registration/password_reset_complete.html'