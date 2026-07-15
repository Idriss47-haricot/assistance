# helpdesk/admin.py - Personnalisation globale
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin
from apps.users.models import User
from apps.tickets.models import Ticket, Comment, Attachment, AuditLog

# ⚠️ SUPPRIMER LES MODÈLES PAR DÉFAUT
admin.site.unregister(Group)

# Ne garder que ce que vous voulez afficher
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Informations', {'fields': ('first_name', 'last_name', 'email', 'phone_number', 'department')}),
        ('Rôle', {'fields': ('role',)}),
        ('Statut', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {'fields': ('username', 'email', 'first_name', 'last_name', 'role', 'password1', 'password2')}),
    )

# Ne pas enregistrer d'autres modèles si vous ne voulez pas les voir
# @admin.register(Ticket)
# class TicketAdmin(admin.ModelAdmin):
#     pass