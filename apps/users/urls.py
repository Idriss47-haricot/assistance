from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views
from django.http import HttpResponse

app_name = 'users'

urlpatterns = [
    # Authentification
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    
    # Profil
    path('profile/', views.profile_view, name='profile'),
    path('change-password/', views.change_password_view, name='change_password'),
    
    # Gestion des utilisateurs (admin)
    path('users/', views.user_list_view, name='user_list'),
    path('users/<uuid:pk>/edit/', views.user_edit_view, name='user_edit'),
    path('users/<uuid:pk>/delete/', views.user_delete_view, name='user_delete'),
    
    # Réinitialisation de mot de passe
    path('password-reset/',
         views.CustomPasswordResetView.as_view(),
         name='password_reset'),
    path('password-reset/done/',
         views.CustomPasswordResetDoneView.as_view(),
         name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/',
         views.CustomPasswordResetConfirmView.as_view(),
         name='password_reset_confirm'),
    path('password-reset/complete/',
         views.CustomPasswordResetCompleteView.as_view(),
         name='password_reset_complete'),


     # Réinitialisation de mot de passe (optionnel)
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='registration/password_reset_form.html'
         ), 
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='registration/password_reset_done.html'
         ), 
         name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='registration/password_reset_confirm.html'
         ), 
         name='password_reset_confirm'),
    path('password-reset/complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='registration/password_reset_complete.html'
         ), 
         name='password_reset_complete'),

]

def profile(request):
    return HttpResponse("Profil utilisateur")

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/', profile, name='profile'),
]