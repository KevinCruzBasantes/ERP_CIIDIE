from django import forms
from .models import Maquina
from usuarios.models import Usuario


class MaquinaForm(forms.ModelForm):

    class Meta:
        model = Maquina
        fields = [
            'nombre', 'codigo', 'numero_serie', 'codigo_barras_universidad',
            'fabricante', 'modelo', 'anio_fabricacion', 'ubicacion',
            'descripcion', 'estado', 'responsable',
            'imagen', 'manual_pdf',
            'voltaje_v', 'frecuencia_hz',
            'presion_neumatica_min_bar', 'presion_neumatica_max_bar',
            'capacidad_refrigerante_l', 'rpm_husillo_max',
            'tipo_control_cnc', 'peso_kg',
            'largo_mm', 'ancho_mm', 'alto_mm',
            'fecha_adquisicion',
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'style': 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none;',
                'placeholder': 'Nombre de la máquina',
            }),
            'codigo': forms.TextInput(attrs={
                'style': 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none;',
                'placeholder': 'Ej: CNC-001',
            }),
            'numero_serie': forms.TextInput(attrs={
                'style': 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none;',
            }),
            'codigo_barras_universidad': forms.TextInput(attrs={
                'style': 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none;',
            }),
            'fabricante': forms.TextInput(attrs={
                'style': 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none;',
            }),
            'modelo': forms.TextInput(attrs={
                'style': 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none;',
            }),
            'anio_fabricacion': forms.NumberInput(attrs={
                'style': 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none;',
                'placeholder': 'Ej: 2020',
            }),
            'ubicacion': forms.TextInput(attrs={
                'style': 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none;',
                'placeholder': 'Ej: Laboratorio CIIDIE — Planta baja',
            }),
            'descripcion': forms.Textarea(attrs={
                'style': 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.85rem; outline:none; resize:vertical;',
                'rows': 3,
            }),
            'estado': forms.Select(attrs={
                'style': 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none; cursor:pointer;',
            }),
            'responsable': forms.Select(attrs={
                'style': 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none; cursor:pointer;',
            }),
            'voltaje_v': forms.NumberInput(attrs={
                'style': 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none;',
                'placeholder': 'Ej: 400',
            }),
            'frecuencia_hz': forms.NumberInput(attrs={
                'style': 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none;',
                'placeholder': 'Ej: 50',
            }),
            'presion_neumatica_min_bar': forms.NumberInput(attrs={
                'style': 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none;',
                'step': '0.1',
            }),
            'presion_neumatica_max_bar': forms.NumberInput(attrs={
                'style': 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none;',
                'step': '0.1',
            }),
            'capacidad_refrigerante_l': forms.NumberInput(attrs={
                'style': 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none;',
                'step': '0.01',
            }),
            'rpm_husillo_max': forms.NumberInput(attrs={
                'style': 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none;',
            }),
            'tipo_control_cnc': forms.TextInput(attrs={
                'style': 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none;',
                'placeholder': 'Ej: Siemens Sinumerik 828D',
            }),
            'peso_kg': forms.NumberInput(attrs={
                'style': 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none;',
                'step': '0.01',
            }),
            'largo_mm': forms.NumberInput(attrs={
                'style': 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none;',
            }),
            'ancho_mm': forms.NumberInput(attrs={
                'style': 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none;',
            }),
            'alto_mm': forms.NumberInput(attrs={
                'style': 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none;',
            }),
            'fecha_adquisicion': forms.DateInput(attrs={
                'style': 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none;',
                'type': 'date',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['responsable'].queryset = Usuario.objects.filter(estado='ACTIVO')
        self.fields['responsable'].empty_label = '— Sin responsable asignado —'
        for field in self.fields.values():
            field.required = False
        self.fields['nombre'].required = True
        self.fields['codigo'].required = True
        self.fields['ubicacion'].required = True
        self.fields['estado'].required = True