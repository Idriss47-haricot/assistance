# apps/users/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UserChangeForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

User = get_user_model()


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
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        role = cleaned_data.get('role')
        
        if username and password and role:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise ValidationError(
                    'Nom d\'utilisateur ou mot de passe incorrect.',
                    code='invalid_login'
                )
            
            if not user.check_password(password):
                raise ValidationError(
                    'Nom d\'utilisateur ou mot de passe incorrect.',
                    code='invalid_login'
                )
            
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