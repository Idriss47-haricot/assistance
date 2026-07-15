# apps/tickets/forms.py - VERSION CORRIGÉE
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from .models import Ticket, Comment, Attachment
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UserChangeForm


User = get_user_model()


class MultipleFileInput(forms.ClearableFileInput):
    """
    Widget personnalisé pour permettre le téléchargement de plusieurs fichiers
    """
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """
    Champ personnalisé pour gérer plusieurs fichiers
    """
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class TicketCreateForm(forms.ModelForm):
    """
    Formulaire de création de ticket
    """
    attachments = MultipleFileField(
        required=False,
        label=_('Pièces jointes'),
        help_text=_('Vous pouvez joindre plusieurs fichiers (max 5Mo par fichier)')
    )
    
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'category', 'priority']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Titre du problème')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': _('Décrivez votre problème en détail...')
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
        labels = {
            'title': _('Titre'),
            'description': _('Description'),
            'category': _('Catégorie'),
            'priority': _('Priorité'),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Ajouter des classes CSS
        for field_name, field in self.fields.items():
            if hasattr(field, 'widget') and 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
    
    def clean_title(self):
        title = self.cleaned_data.get('title')
        if len(title) < 3:
            raise ValidationError(_('Le titre doit contenir au moins 3 caractères.'))
        return title
    
    def clean_attachments(self):
        files = self.files.getlist('attachments')
        max_size = 5 * 1024 * 1024  # 5 Mo
        
        for file in files:
            if file.size > max_size:
                raise ValidationError(
                    _(f'Le fichier "{file.name}" dépasse la taille maximale de 5 Mo.')
                )
        
        return files
    
    def save(self, commit=True):
        ticket = super().save(commit=False)
        ticket.created_by = self.user
        
        if commit:
            ticket.save()
            # Sauvegarder les pièces jointes
            files = self.files.getlist('attachments')
            for file in files:
                Attachment.objects.create(
                    ticket=ticket,
                    file=file,
                    filename=file.name,
                    uploaded_by=self.user
                )
        
        return ticket


class TicketEditForm(forms.ModelForm):
    """
    Formulaire d'édition de ticket (pour admin/technicien)
    """
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(is_staff=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'category', 'priority', 'status', 'assigned_to']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrer les techniciens disponibles
        self.fields['assigned_to'].queryset = User.objects.filter(
            is_staff=True,
            is_active=True
        ).order_by('username')


class TicketStatusForm(forms.Form):
    """
    Formulaire de changement de statut
    """
    status = forms.ChoiceField(
        choices=Ticket.Status.choices,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('Ajouter un commentaire (optionnel)...')
        })
    )


class CommentForm(forms.ModelForm):
    """
    Formulaire de commentaire
    """
    class Meta:
        model = Comment
        fields = ['content', 'is_internal']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Écrire un commentaire...')
            }),
            'is_internal': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'content': _('Commentaire'),
            'is_internal': _('Commentaire interne (visible uniquement par les techniciens)'),
        }
    
    def clean_content(self):
        content = self.cleaned_data.get('content')
        if len(content) < 2:
            raise ValidationError(_('Le commentaire doit contenir au moins 2 caractères.'))
        return content


class TicketSearchForm(forms.Form):
    """
    Formulaire de recherche de tickets
    """
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Rechercher un ticket...')
        })
    )
    status = forms.ChoiceField(
        required=False,
        choices=[('', _('Tous les statuts'))] + Ticket.Status.choices,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    priority = forms.ChoiceField(
        required=False,
        choices=[('', _('Toutes les priorités'))] + Ticket.Priority.choices,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    category = forms.ChoiceField(
        required=False,
        choices=[('', _('Toutes les catégories'))] + Ticket.Category.choices,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    assigned_to = forms.ChoiceField(
        required=False,
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Remplir les choix des techniciens
        technicians = User.objects.filter(
            is_staff=True,
            is_active=True
        ).order_by('username')
        
        choices = [('', _('Tous les techniciens'))]
        choices.extend([(str(u.id), u.get_full_name() or u.username) for u in technicians])
        self.fields['assigned_to'].choices = choices



# ============================================================
# FORMULAIRE DE CONNEXION AVEC RÔLE
# ============================================================

class RoleLoginForm(AuthenticationForm):
    """
    Formulaire de connexion avec sélection de rôle
    """
    ROLE_CHOICES = [
        ('', '--- Choisissez votre rôle ---'),
        ('ADMIN', '👑 Administrateur'),
        ('MANAGER', '👨‍🔧 Manager'),
        ('TECHNICIAN', '🔧 Technicien'),
        ('EMPLOYEE', '👤 Employé'),
    ]
    
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select role-select',
            'id': 'role-select'
        }),
        label='Je suis'
    )
    
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nom d\'utilisateur',
            'autofocus': True
        }),
        label='Nom d\'utilisateur'
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mot de passe'
        }),
        label='Mot de passe'
    )
    
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Se souvenir de moi'
    )
    
    def clean(self):
        """
        Vérifier que le rôle sélectionné correspond au rôle de l'utilisateur
        """
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        role = cleaned_data.get('role')
        
        if username and password and role:
            # Récupérer l'utilisateur
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise ValidationError(
                    'Nom d\'utilisateur ou mot de passe incorrect.',
                    code='invalid_login'
                )
            
            # Vérifier le mot de passe
            if not user.check_password(password):
                raise ValidationError(
                    'Nom d\'utilisateur ou mot de passe incorrect.',
                    code='invalid_login'
                )
            
            # Vérifier le rôle
            user_role = user.role
            role_mapping = {
                'ADMIN': ['ADMIN'],
                'MANAGER': ['MANAGER', 'ADMIN'],
                'TECHNICIAN': ['TECHNICIAN', 'MANAGER', 'ADMIN'],
                'EMPLOYEE': ['EMPLOYEE', 'TECHNICIAN', 'MANAGER', 'ADMIN'],
            }
            
            if user_role not in role_mapping.get(role, []):
                raise ValidationError(
                    f'Vous avez sélectionné le rôle "{dict(self.ROLE_CHOICES).get(role)}" '
                    f'mais votre compte est "{user.get_role_display()}". '
                    f'Veuillez sélectionner le bon rôle.',
                    code='role_mismatch'
                )
            
            # Stocker l'utilisateur pour le login
            self.user_cache = user
        
        return cleaned_data


# ============================================================
# FORMULAIRE D'INSCRIPTION
# ============================================================

class CustomUserCreationForm(UserCreationForm):
    """
    Formulaire d'inscription personnalisé
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    first_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Prénom'})
    )
    last_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom'})
    )
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    department = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Département'})
    )
    phone_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Téléphone'})
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 
                 'department', 'phone_number', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError(_('Un utilisateur avec cet email existe déjà.'))
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


# ============================================================
# FORMULAIRE DE MODIFICATION (ADMIN)
# ============================================================

class CustomUserChangeForm(UserChangeForm):
    """
    Formulaire de modification utilisateur (admin)
    """
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'role',
                 'department', 'phone_number', 'avatar', 'bio', 'is_active', 'is_staff', 'is_superuser')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise ValidationError(_('Un utilisateur avec cet email existe déjà.'))
        return email


# ============================================================
# FORMULAIRE DE PROFIL (UTILISATEUR CONNECTÉ)
# ============================================================

class UserProfileForm(forms.ModelForm):
    """
    Formulaire de profil utilisateur (pour l'utilisateur connecté)
    """
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'phone_number', 
                 'department', 'avatar', 'bio')
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        user = self.instance
        if User.objects.exclude(pk=user.pk).filter(email=email).exists():
            raise ValidationError(_('Un utilisateur avec cet email existe déjà.'))
        return email