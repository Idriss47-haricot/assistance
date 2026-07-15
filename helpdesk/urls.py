from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView


def home(request):
    return render(request, 'base.html')

@login_required
def dashboard(request):
    return render(request, 'dashboard.html')

@login_required
def profile(request):
    return render(request, 'profile.html')

urlpatterns = [
    # Admin Django (seulement pour les admins)
    path('admin/', admin.site.urls),
    
    # Pages publiques
    path('', home, name='home'),
    
    # Pages protégées (nécessitent connexion)
    path('dashboard/', login_required(dashboard), name='dashboard'),
    path('profile/', login_required(profile), name='profile'),
    
    # Connexion / Déconnexion (pour TOUS les utilisateurs)
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    
    path('logout/', auth_views.LogoutView.as_view(
        next_page='home'
    ), name='logout'),
    
    # Applications
    path('tickets/', include('apps.tickets.urls')),
    path('', include('apps.users.urls')), 


]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)