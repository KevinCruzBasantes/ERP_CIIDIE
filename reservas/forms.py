from django import forms
from django.utils import timezone
from .models import Reserva, OrdenTrabajo, RegistroParada, BitacoraOperario
from maquinas.models import Maquina, CodigoParada

FIELD_STYLE    = 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none;'
SELECT_STYLE   = 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none; cursor:pointer;'
TEXTAREA_STYLE = 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.85rem; outline:none; resize:vertical;'


class ReservaForm(forms.ModelForm):
    class Meta:
        model  = Reserva
        fields = ['maquina', 'fecha', 'hora_inicio', 'hora_fin', 'proposito', 'observaciones']
        widgets = {
            'maquina':       forms.Select(attrs={'style': SELECT_STYLE}),
            'fecha':         forms.DateInput(attrs={'style': FIELD_STYLE, 'type': 'date'}),
            'hora_inicio':   forms.TimeInput(attrs={'style': FIELD_STYLE, 'type': 'time'}),
            'hora_fin':      forms.TimeInput(attrs={'style': FIELD_STYLE, 'type': 'time'}),
            'proposito':     forms.Select(attrs={'style': SELECT_STYLE}),
            'observaciones': forms.Textarea(attrs={'style': TEXTAREA_STYLE, 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['maquina'].queryset    = Maquina.objects.filter(estado='OPERATIVA').order_by('nombre')
        self.fields['maquina'].empty_label = '— Seleccionar máquina —'
        self.fields['observaciones'].required = False
        self.fields['fecha'].widget.attrs['min'] = timezone.now().date().isoformat()

    def clean(self):
        cleaned = super().clean()
        h_ini = cleaned.get('hora_inicio')
        h_fin = cleaned.get('hora_fin')
        if h_ini and h_fin and h_fin <= h_ini:
            raise forms.ValidationError('La hora de fin debe ser posterior a la hora de inicio.')
        return cleaned


class OrdenTrabajoForm(forms.ModelForm):
    class Meta:
        model  = OrdenTrabajo
        fields = ['descripcion', 'tiempo_planificado_min', 'unidades_esperadas']
        widgets = {
            'descripcion':             forms.Textarea(attrs={'style': TEXTAREA_STYLE, 'rows': 3}),
            'tiempo_planificado_min':  forms.NumberInput(attrs={'style': FIELD_STYLE, 'step': '1'}),
            'unidades_esperadas':      forms.NumberInput(attrs={'style': FIELD_STYLE, 'step': '1'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['unidades_esperadas'].required = False


class CerrarOrdenForm(forms.ModelForm):
    class Meta:
        model  = OrdenTrabajo
        fields = ['tiempo_real_min', 'tiempo_parada_min', 'unidades_producidas',
                  'unidades_sin_defecto', 'resultado']
        widgets = {
            'tiempo_real_min':     forms.NumberInput(attrs={'style': FIELD_STYLE, 'step': '1'}),
            'tiempo_parada_min':   forms.NumberInput(attrs={'style': FIELD_STYLE, 'step': '1'}),
            'unidades_producidas': forms.NumberInput(attrs={'style': FIELD_STYLE, 'step': '1'}),
            'unidades_sin_defecto':forms.NumberInput(attrs={'style': FIELD_STYLE, 'step': '1'}),
            'resultado':           forms.Textarea(attrs={'style': TEXTAREA_STYLE, 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ['tiempo_parada_min', 'unidades_producidas', 'unidades_sin_defecto', 'resultado']:
            self.fields[f].required = False


class RegistroParadaForm(forms.ModelForm):
    class Meta:
        model  = RegistroParada
        fields = ['codigo_parada', 'hora_inicio', 'hora_fin', 'descripcion_tecnica']
        widgets = {
            'codigo_parada':       forms.Select(attrs={'style': SELECT_STYLE}),
            'hora_inicio':         forms.TimeInput(attrs={'style': FIELD_STYLE, 'type': 'time'}),
            'hora_fin':            forms.TimeInput(attrs={'style': FIELD_STYLE, 'type': 'time'}),
            'descripcion_tecnica': forms.Textarea(attrs={'style': TEXTAREA_STYLE, 'rows': 2}),
        }

    def __init__(self, *args, maquina=None, **kwargs):
        super().__init__(*args, **kwargs)
        if maquina:
            self.fields['codigo_parada'].queryset = CodigoParada.objects.filter(
                fabricante=maquina.fabricante,
                modelo_maquina=maquina.modelo
            )
        self.fields['codigo_parada'].empty_label = '— Sin código catalogado —'
        self.fields['codigo_parada'].required    = False
        self.fields['hora_fin'].required         = False


class BitacoraForm(forms.ModelForm):
    class Meta:
        model  = BitacoraOperario
        fields = ['descripcion_trabajo', 'observaciones', 'requiere_atencion']
        widgets = {
            'descripcion_trabajo': forms.Textarea(attrs={'style': TEXTAREA_STYLE, 'rows': 3}),
            'observaciones':       forms.Textarea(attrs={'style': TEXTAREA_STYLE, 'rows': 2}),
            'requiere_atencion':   forms.CheckboxInput(attrs={'style': 'width:16px;height:16px;cursor:pointer;accent-color:#e8a020;'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['observaciones'].required    = False
        self.fields['requiere_atencion'].required = False