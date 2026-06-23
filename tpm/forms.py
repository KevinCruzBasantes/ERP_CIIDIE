from django import forms
from django.utils import timezone
from .models import CertificacionUsuario, RegistroOEE, Incidente, HallazgoInspeccion, ItemChecklistInspeccion

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

    def __init__(self, *args, usuario_actual=None, **kwargs):
        super().__init__(*args, **kwargs)
        from usuarios.models import Usuario
        from maquinas.models import Maquina
        self.usuario_actual = usuario_actual
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
        usuario = cleaned.get('usuario')
        if usuario and self.usuario_actual and usuario.pk == self.usuario_actual.pk:
            raise forms.ValidationError(
                'No puedes otorgarte una certificación a ti mismo. Otra persona calificada debe certificarte.'
            )
        return cleaned


class IncidenteForm(forms.ModelForm):
    class Meta:
        model  = Incidente
        fields = [
            'maquina', 'tipo', 'severidad',
            'fecha_ocurrencia', 'descripcion',
            'accion_tomada', 'requiere_mantenimiento',
        ]
        widgets = {
            'maquina':            forms.Select(attrs={'style': SELECT_STYLE}),
            'tipo':               forms.Select(attrs={'style': SELECT_STYLE}),
            'severidad':          forms.Select(attrs={'style': SELECT_STYLE}),
            'fecha_ocurrencia':   forms.DateTimeInput(
                attrs={'style': FIELD_STYLE, 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'descripcion':        forms.Textarea(attrs={
                'style': TEXTAREA_STYLE, 'rows': 4,
                'placeholder': 'Describe qué ocurrió, en qué condiciones y cuál fue el impacto observado.',
            }),
            'accion_tomada':      forms.Textarea(attrs={
                'style': TEXTAREA_STYLE, 'rows': 3,
                'placeholder': 'Acciones inmediatas tomadas para controlar el incidente.',
            }),
            'requiere_mantenimiento': forms.CheckboxInput(
                attrs={'style': 'width:16px; height:16px; cursor:pointer; accent-color:#e8a020;'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from maquinas.models import Maquina
        self.fields['maquina'].queryset   = Maquina.objects.all().order_by('nombre')
        self.fields['maquina'].empty_label = '— Seleccionar máquina —'
        self.fields['accion_tomada'].required       = False
        self.fields['requiere_mantenimiento'].required = False
        self.fields['fecha_ocurrencia'].input_formats = [
            '%Y-%m-%dT%H:%M',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
        ]


class HallazgoForm(forms.ModelForm):
    class Meta:
        model  = HallazgoInspeccion
        fields = ['descripcion', 'prioridad', 'resuelto']
        widgets = {
            'descripcion': forms.Textarea(attrs={
                'style': TEXTAREA_STYLE, 'rows': 3,
                'placeholder': 'Describe el hallazgo encontrado durante la inspección.',
            }),
            'prioridad': forms.Select(attrs={'style': SELECT_STYLE}),
            'resuelto':  forms.CheckboxInput(
                attrs={'style': 'width:16px; height:16px; cursor:pointer; accent-color:#e8a020;'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['resuelto'].required = False


class ItemChecklistForm(forms.ModelForm):

    class Meta:
        model  = ItemChecklistInspeccion
        fields = ['fabricante', 'modelo_maquina', 'nombre', 'descripcion', 'es_critico', 'orden']
        widgets = {
            'fabricante':     forms.TextInput(attrs={'style': FIELD_STYLE, 'placeholder': 'Nombre del fabricante'}),
            'modelo_maquina': forms.TextInput(attrs={'style': FIELD_STYLE, 'placeholder': 'Modelo de la máquina'}),
            'nombre':         forms.TextInput(attrs={
                'style': FIELD_STYLE,
                'placeholder': 'Ej: Nivel de aceite de lubricación OK',
            }),
            'descripcion':    forms.Textarea(attrs={
                'style': TEXTAREA_STYLE, 'rows': 2,
                'placeholder': 'Criterio de aceptación o detalle adicional (opcional)',
            }),
            'es_critico':     forms.CheckboxInput(
                attrs={'style': 'width:16px; height:16px; cursor:pointer; accent-color:#e8a020;'}
            ),
            'orden':          forms.NumberInput(attrs={'style': FIELD_STYLE, 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['descripcion'].required = False
        self.fields['orden'].required = False

        # Poblar datalists con valores ya existentes, igual que CodigoParadaForm
        fabricantes = ItemChecklistInspeccion.objects.values_list('fabricante', flat=True).distinct().order_by('fabricante')
        modelos     = ItemChecklistInspeccion.objects.values_list('modelo_maquina', flat=True).distinct().order_by('modelo_maquina')
        self.fabricantes_existentes = list(fabricantes)
        self.modelos_existentes     = list(modelos)