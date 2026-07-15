# apps/tickets/validators.py
import os
import magic
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_file_extension(value):
    """
    Valide l'extension du fichier
    """
    ext = os.path.splitext(value.name)[1].lower()
    allowed_extensions = [
        '.jpg', '.jpeg', '.png', '.gif', '.pdf',
        '.doc', '.docx', '.xls', '.xlsx', '.txt',
        '.zip', '.rar', '.7z'
    ]
    
    if ext not in allowed_extensions:
        raise ValidationError(
            _('Extension de fichier non autorisée. '
              'Extensions autorisées: jpg, jpeg, png, gif, pdf, doc, docx, xls, xlsx, txt, zip, rar, 7z')
        )


def validate_file_size(value):
    """
    Valide la taille du fichier (max 10 Mo)
    """
    max_size = 10 * 1024 * 1024  # 10 Mo
    
    if value.size > max_size:
        raise ValidationError(
            _(f'Le fichier est trop volumineux. Taille maximale: {max_size // (1024 * 1024)} Mo')
        )


def validate_file_mime_type(value):
    """
    Valide le type MIME du fichier
    """
    # Détecter le type MIME réel
    mime = magic.from_buffer(value.read(1024), mime=True)
    value.seek(0)  # Réinitialiser le pointeur
    
    allowed_mimes = [
        'image/jpeg', 'image/png', 'image/gif',
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/plain',
        'application/zip',
        'application/x-rar-compressed',
    ]
    
    if mime not in allowed_mimes:
        raise ValidationError(
            _('Type de fichier non autorisé. '
              'Veuillez uploader des images, documents Office, PDF ou archives.')
        )


# Utilisation dans le modèle Attachment
class Attachment(models.Model):
    # ...
    file = models.FileField(
        _('Fichier'),
        upload_to='tickets/%Y/%m/%d/',
        max_length=255,
        validators=[validate_file_extension, validate_file_size, validate_file_mime_type]
    )