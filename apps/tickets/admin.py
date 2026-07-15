from django.contrib import admin
from .models import Ticket, Comment, Attachment, AuditLog

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    """
    Administration des tickets
    """
    list_display = ('reference', 'title', 'status', 'priority', 'category', 'created_by', 'created_at')
    list_filter = ('status', 'priority', 'category', 'created_at')
    search_fields = ('reference', 'title', 'description')
    readonly_fields = ('reference', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Informations principales', {
            'fields': ('reference', 'title', 'description', 'category', 'priority', 'status')
        }),
        ('Utilisateurs', {
            'fields': ('created_by', 'assigned_to')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at', 'resolved_at', 'closed_at')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """
    Administration des commentaires
    """
    list_display = ('ticket', 'user', 'content', 'created_at')
    list_filter = ('is_internal', 'created_at')
    search_fields = ('content',)


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    """
    Administration des pièces jointes
    """
    list_display = ('filename', 'ticket', 'uploaded_by', 'uploaded_at')
    search_fields = ('filename',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Administration des journaux d'audit
    """
    list_display = ('ticket', 'user', 'action', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('old_value', 'new_value')
    readonly_fields = ('ticket', 'user', 'action', 'old_value', 'new_value', 'created_at')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False