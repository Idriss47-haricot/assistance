from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    # Liste et création
    path('', views.ticket_list, name='list'),
    path('create/', views.ticket_create, name='create'),
    path('export/', views.ticket_export, name='export'),

    # Détail et édition
    path('<uuid:pk>/', views.ticket_detail, name='detail'),
    path('<uuid:pk>/edit/', views.ticket_edit, name='edit'),
    path('<uuid:pk>/delete/', views.ticket_delete, name='delete'),

    # Actions
    path('<uuid:pk>/status/', views.ticket_change_status, name='change_status'),
    path('<uuid:pk>/assign/', views.ticket_assign, name='assign'),
    path('<uuid:pk>/unassign/', views.ticket_unassign, name='unassign'),

    # Commentaires
    path('comments/<uuid:pk>/delete/', views.comment_delete, name='comment_delete'),
    path('comments/<uuid:pk>/edit/', views.comment_edit, name='comment_edit'),
    path('<uuid:pk>/take/', views.ticket_take, name='take'),      # ← AJOUT
    path('<uuid:pk>/unassign/', views.ticket_unassign, name='unassign'),  #
    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),

    path('<uuid:pk>/assign/', views.ticket_assign, name='assign'),  # ← AJOUT
    path('export/pdf/', views.ticket_export_pdf, name='export_pdf'),
    
    path('assign-from-dashboard/', views.ticket_assign_from_dashboard, name='assign_from_dashboard'),
        # Notifications (AJAX)
    path('notifications/', views.get_notifications, name='get_notifications'),
    path('notifications/<uuid:pk>/read/', views.mark_notification_read, name='mark_notification_read'),

    # Export PDF
    path('export/single/<uuid:pk>/', views.ticket_export_single_pdf, name='export_single_pdf'),
    path('export/all/', views.ticket_export_all_pdf, name='export_all_pdf'),
    
        # Rapports
    path('report/', views.report_view, name='report'),
    path('report/generate/', views.report_generate, name='report_generate'),
    
    # Assignation en masse
    path('assign-mass/', views.ticket_assign_mass, name='assign_mass'),

        # Statistiques avancées
    path('stats/', views.stats_advanced, name='stats_advanced'),

    path('<uuid:pk>/assign-by-manager/', views.ticket_assign_by_manager, name='assign_by_manager'),



]