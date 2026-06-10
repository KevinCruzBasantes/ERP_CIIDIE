from django import forms
from .models import Material

FIELD_STYLE    = 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none;'
SELECT_STYLE   = 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none; cursor:pointer;'
TEXTAREA_STYLE = 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.85rem; outline:none; resize:vertical;'


class MaterialForm(forms.ModelForm):
    class Meta:
        model  = Material
        fields = ['codigo', 'nombre', 'tipo', 'descripcion', 'proveedor',
                  'stock_actual', 'stock_minimo', 'unidad_medida', 'costo_unitario', 'activo']
        widgets = {
            'codigo':         forms.TextInput(attrs={'style': FIELD_STYLE, 'placeholder': 'Ej: MAT-001'}),
            'nombre':         forms.TextInput(attrs={'style': FIELD_STYLE}),
            'tipo':           forms.Select(attrs={'style': SELECT_STYLE}),
            'descripcion':    forms.Textarea(attrs={'style': TEXTAREA_STYLE, 'rows': 2}),
            'proveedor':      forms.TextInput(attrs={'style': FIELD_STYLE}),
            'stock_actual':   forms.NumberInput(attrs={'style': FIELD_STYLE, 'step': '0.01'}),
            'stock_minimo':   forms.NumberInput(attrs={'style': FIELD_STYLE, 'step': '0.01'}),
            'unidad_medida':  forms.TextInput(attrs={'style': FIELD_STYLE, 'placeholder': 'Ej: unidad, litro, kg'}),
            'costo_unitario': forms.NumberInput(attrs={'style': FIELD_STYLE, 'step': '0.01'}),
            'activo':         forms.CheckboxInput(attrs={'style': 'width:16px;height:16px;cursor:pointer;accent-color:#e8a020;'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['descripcion'].required = False
        self.fields['proveedor'].required   = False