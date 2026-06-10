from django import forms
from .models import Mantenimiento, PlanMantenimiento
from maquinas.models import Maquina
from usuarios.models import Usuario

FIELD_STYLE = 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none;'
SELECT_STYLE = 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none; cursor:pointer;'
TEXTAREA_STYLE = 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.85rem; outline:none; resize:vertical;'


class MantenimientoForm(forms.ModelForm):

    class Meta:
        model = Mantenimiento
        fields = [
            'maquina', 'plan', 'responsable', 'tipo', 'estado',
            'prioridad', 'fecha_programada', 'fecha_inicio', 'fecha_fin',
            'proxima_fecha', 'descripcion', 'acciones_realizadas',
            'observaciones', 'horas_trabajo', 'costo',
        ]
        widgets = {
            'maquina': forms.Select(attrs={'style': SELECT_STYLE}),
            'plan': forms.Select(attrs={'style': SELECT_STYLE}),
            'responsable': forms.Select(attrs={'style': SELECT_STYLE}),
            'tipo': forms.Select(attrs={'style': SELECT_STYLE}),
            'estado': forms.Select(attrs={'style': SELECT_STYLE}),
            'prioridad': forms.Select(attrs={'style': SELECT_STYLE}),
            'fecha_programada': forms.DateInput(attrs={
                'style': FIELD_STYLE, 'type': 'date'
            }),
            'fecha_inicio': forms.DateTimeInput(attrs={
                'style': FIELD_STYLE, 'type': 'datetime-local'
            }),
            'fecha_fin': forms.DateTimeInput(attrs={
                'style': FIELD_STYLE, 'type': 'datetime-local'
            }),
            'proxima_fecha': forms.DateInput(attrs={
                'style': FIELD_STYLE, 'type': 'date'
            }),
            'descripcion': forms.Textarea(attrs={
                'style': TEXTAREA_STYLE, 'rows': 3,
                'placeholder': 'Describe el trabajo a realizar o realizado'
            }),
            'acciones_realizadas': forms.Textarea(attrs={
                'style': TEXTAREA_STYLE, 'rows': 3,
            }),
            'observaciones': forms.Textarea(attrs={
                'style': TEXTAREA_STYLE, 'rows': 2,
            }),
            'horas_trabajo': forms.NumberInput(attrs={
                'style': FIELD_STYLE, 'step': '0.01', 'placeholder': '0.00'
            }),
            'costo': forms.NumberInput(attrs={
                'style': FIELD_STYLE, 'step': '0.01', 'placeholder': '0.00'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['maquina'].queryset = Maquina.objects.all().order_by('nombre')
        self.fields['plan'].queryset = PlanMantenimiento.objects.filter(
            activo=True
        ).select_related('maquina').order_by('maquina__nombre')
        self.fields['plan'].empty_label = '— Sin plan asociado (correctivo) —'
        self.fields['responsable'].queryset = Usuario.objects.filter(
            estado='ACTIVO'
        ).order_by('first_name')
        self.fields['responsable'].empty_label = '— Sin responsable asignado —'
        self.fields['fecha_inicio'].required = False
        self.fields['fecha_fin'].required = False
        self.fields['proxima_fecha'].required = False
        self.fields['plan'].required = False
        self.fields['responsable'].required = False
        self.fields['acciones_realizadas'].required = False
        self.fields['observaciones'].required = False
        self.fields['descripcion'].required = True
        self.fields['maquina'].required = True
        self.fields['fecha_programada'].required = True