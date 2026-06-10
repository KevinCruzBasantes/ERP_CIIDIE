from django import forms
from django.utils import timezone
from .models import CertificacionUsuario, RegistroOEE, Incidente

FIELD_STYLE    = 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none;'
SELECT_STYLE   = 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none; cursor:pointer;'
TEXTAREA_STYLE = 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.85rem; outline:none; resize:vertical;'


class CertificacionForm(forms.ModelForm):
    class Meta:
        model  = CertificacionUsuario
        fields = ['usuario', 'maquina', 'fecha_otorgamiento', 'fecha_vencimiento', 'observaciones']
        widgets = {
            'usuario':            forms.Select(attrs={'style': SELECT_STYLE}),
            'maquina':            forms.Select(attrs={'style': SELECT_STYLE}),
            'fecha_otorgamiento': forms.DateInput(
                attrs={'style': FIELD_STYLE, 'type': 'date'},
                format='%Y-%m-%d'
            ),
            'fecha_vencimiento':  forms.DateInput(
                attrs={'style': FIELD_STYLE, 'type': 'date'},
                format='%Y-%m-%d'
            ),
            'observaciones':      forms.Textarea(attrs={'style': TEXTAREA_STYLE, 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from usuarios.models import Usuario
        from maquinas.models import Maquina
        self.fields['usuario'].queryset    = Usuario.objects.filter(estado='ACTIVO').order_by('username')
        self.fields['maquina'].queryset    = Maquina.objects.filter(estado='OPERATIVA').order_by('nombre')
        self.fields['observaciones'].required = False
        self.fields['fecha_otorgamiento'].input_formats = ['%Y-%m-%d']
        self.fields['fecha_vencimiento'].input_formats  = ['%Y-%m-%d']

    def clean(self):
        cleaned = super().clean()
        f_oto = cleaned.get('fecha_otorgamiento')
        f_ven = cleaned.get('fecha_vencimiento')
        if f_oto and f_ven and f_ven <= f_oto:
            raise forms.ValidationError('La fecha de vencimiento debe ser posterior a la fecha de otorgamiento.')
        return cleaned