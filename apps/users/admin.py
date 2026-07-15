# apps/users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from .models import User

# ⚠️ SUPPRIMER LE MODÈLE GROUPES DE L'ADMIN
admin.site.unregister(Group)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Administration des utilisateurs personnalisée
    """
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active')
    list_filter = ('role', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Informations personnelles', {
            'fields': ('first_name', 'last_name', 'email', 'phone_number', 'department')
        }),
        ('Rôle', {'fields': ('role',)}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'role', 
                      'department', 'phone_number', 'password1', 'password2'),
        }),
    )