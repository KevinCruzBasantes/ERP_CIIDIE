from django import forms
from django.contrib.auth.password_validation import validate_password
from .models import Usuario, Rol, DisponibilidadOperador


FIELD_STYLE = 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none;'
SELECT_STYLE = 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none; cursor:pointer;'
HORA_ATTRS = {'style': FIELD_STYLE, 'type': 'text', 'placeholder': 'HH:MM', 'pattern': r'([01][0-9]|2[0-3]):[0-5][0-9]'}


class UsuarioCrearForm(forms.ModelForm):

    password1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'style': FIELD_STYLE, 'placeholder': 'Mínimo 8 caracteres'}),
    )
    password2 = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={'style': FIELD_STYLE, 'placeholder': 'Repite la contraseña'}),
    )

    class Meta:
        model = Usuario
        fields = [
            'username', 'first_name', 'last_name',
            'email', 'cedula', 'telefono', 'rol', 'estado',
        ]
        widgets = {
            'username': forms.TextInput(attrs={'style': FIELD_STYLE, 'placeholder': 'Nombre de usuario'}),
            'first_name': forms.TextInput(attrs={'style': FIELD_STYLE, 'placeholder': 'Nombres'}),
            'last_name': forms.TextInput(attrs={'style': FIELD_STYLE, 'placeholder': 'Apellidos'}),
            'email': forms.EmailInput(attrs={'style': FIELD_STYLE, 'placeholder': 'correo@ejemplo.com'}),
            'cedula': forms.TextInput(attrs={'style': FIELD_STYLE, 'placeholder': '10 dígitos'}),
            'telefono': forms.TextInput(attrs={'style': FIELD_STYLE, 'placeholder': 'Ej: 0991234567'}),
            'rol': forms.Select(attrs={'style': SELECT_STYLE}),
            'estado': forms.Select(attrs={'style': SELECT_STYLE}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rol'].queryset = Rol.objects.all()
        self.fields['rol'].empty_label = '— Sin rol asignado —'
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['cedula'].required = True

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Las contraseñas no coinciden.')
        return p2

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password:
            validate_password(password)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class RegistroEstudianteForm(forms.ModelForm):
    """Autorregistro público: rol y estado quedan fijos (Estudiante / Activo),
    sin aprobación de un administrador o técnico."""

    password1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'style': FIELD_STYLE, 'placeholder': 'Mínimo 8 caracteres'}),
    )
    password2 = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={'style': FIELD_STYLE, 'placeholder': 'Repite la contraseña'}),
    )

    class Meta:
        model = Usuario
        fields = ['username', 'first_name', 'last_name', 'email', 'cedula', 'telefono']
        widgets = {
            'username': forms.TextInput(attrs={'style': FIELD_STYLE, 'placeholder': 'Nombre de usuario'}),
            'first_name': forms.TextInput(attrs={'style': FIELD_STYLE, 'placeholder': 'Nombres'}),
            'last_name': forms.TextInput(attrs={'style': FIELD_STYLE, 'placeholder': 'Apellidos'}),
            'email': forms.EmailInput(attrs={'style': FIELD_STYLE, 'placeholder': 'correo@ejemplo.com'}),
            'cedula': forms.TextInput(attrs={'style': FIELD_STYLE, 'placeholder': '10 dígitos'}),
            'telefono': forms.TextInput(attrs={'style': FIELD_STYLE, 'placeholder': 'Ej: 0991234567'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['cedula'].required = True

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Las contraseñas no coinciden.')
        return p2

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password:
            validate_password(password)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.rol, _ = Rol.objects.get_or_create(nombre='ESTUDIANTE')
        user.estado = 'ACTIVO'
        if commit:
            user.save()
        return user


class DisponibilidadOperadorForm(forms.ModelForm):
    class Meta:
        model  = DisponibilidadOperador
        fields = ['dia_semana', 'hora_inicio', 'hora_fin']
        widgets = {
            'dia_semana':  forms.Select(attrs={'style': SELECT_STYLE}),
            'hora_inicio': forms.TimeInput(attrs=HORA_ATTRS, format='%H:%M'),
            'hora_fin':    forms.TimeInput(attrs=HORA_ATTRS, format='%H:%M'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['hora_inicio'].input_formats = ['%H:%M']
        self.fields['hora_fin'].input_formats    = ['%H:%M']


class UsuarioEditarForm(forms.ModelForm):

    class Meta:
        model = Usuario
        fields = [
            'username', 'first_name', 'last_name',
            'email', 'cedula', 'telefono', 'rol', 'estado',
        ]
        widgets = {
            'username': forms.TextInput(attrs={'style': FIELD_STYLE}),
            'first_name': forms.TextInput(attrs={'style': FIELD_STYLE}),
            'last_name': forms.TextInput(attrs={'style': FIELD_STYLE}),
            'email': forms.EmailInput(attrs={'style': FIELD_STYLE}),
            'cedula': forms.TextInput(attrs={'style': FIELD_STYLE}),
            'telefono': forms.TextInput(attrs={'style': FIELD_STYLE}),
            'rol': forms.Select(attrs={'style': SELECT_STYLE}),
            'estado': forms.Select(attrs={'style': SELECT_STYLE}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rol'].queryset = Rol.objects.all()
        self.fields['rol'].empty_label = '— Sin rol asignado —'
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['cedula'].required = True