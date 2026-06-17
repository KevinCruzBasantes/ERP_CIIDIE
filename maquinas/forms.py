from django import forms
from .models import Maquina, Pieza, TransferenciaPieza, CodigoParada
from usuarios.models import Usuario

INPUT = 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none;'
SELECT = INPUT + ' cursor:pointer;'
TEXTAREA = INPUT + ' resize:vertical;'


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
            'nombre':                    forms.TextInput(attrs={'style': INPUT, 'placeholder': 'Nombre de la máquina'}),
            'codigo':                    forms.TextInput(attrs={'style': INPUT, 'placeholder': 'Ej: CNC-001'}),
            'numero_serie':              forms.TextInput(attrs={'style': INPUT}),
            'codigo_barras_universidad': forms.TextInput(attrs={'style': INPUT}),
            'fabricante':                forms.TextInput(attrs={'style': INPUT}),
            'modelo':                    forms.TextInput(attrs={'style': INPUT}),
            'anio_fabricacion':          forms.NumberInput(attrs={'style': INPUT, 'placeholder': 'Ej: 2020'}),
            'ubicacion':                 forms.TextInput(attrs={'style': INPUT, 'placeholder': 'Ej: Laboratorio CIDIIE — Planta baja'}),
            'descripcion':               forms.Textarea(attrs={'style': TEXTAREA, 'rows': 3}),
            'estado':                    forms.Select(attrs={'style': SELECT}),
            'responsable':               forms.Select(attrs={'style': SELECT}),
            'voltaje_v':                 forms.NumberInput(attrs={'style': INPUT, 'placeholder': 'Ej: 400'}),
            'frecuencia_hz':             forms.NumberInput(attrs={'style': INPUT, 'placeholder': 'Ej: 50'}),
            'presion_neumatica_min_bar': forms.NumberInput(attrs={'style': INPUT, 'step': '0.1'}),
            'presion_neumatica_max_bar': forms.NumberInput(attrs={'style': INPUT, 'step': '0.1'}),
            'capacidad_refrigerante_l':  forms.NumberInput(attrs={'style': INPUT, 'step': '0.01'}),
            'rpm_husillo_max':           forms.NumberInput(attrs={'style': INPUT}),
            'tipo_control_cnc':          forms.TextInput(attrs={'style': INPUT, 'placeholder': 'Tipo de controlador CNC, si aplica'}),
            'peso_kg':                   forms.NumberInput(attrs={'style': INPUT, 'step': '0.01'}),
            'largo_mm':                  forms.NumberInput(attrs={'style': INPUT}),
            'ancho_mm':                  forms.NumberInput(attrs={'style': INPUT}),
            'alto_mm':                   forms.NumberInput(attrs={'style': INPUT}),
            'fecha_adquisicion':         forms.DateInput(attrs={'style': INPUT, 'type': 'date'}),
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


class EnsambleForm(forms.ModelForm):
    """Formulario reducido: un ensamble (Baugruppe) solo necesita identificación, no datos
    técnicos ni stock (un ensamble no se repone como repuesto, las piezas que lo componen sí)."""

    class Meta:
        model = Pieza
        fields = ['nombre', 'nombre_original', 'nombre_en', 'descripcion']
        widgets = {
            'nombre':          forms.TextInput(attrs={'style': INPUT, 'placeholder': 'Nombre en español'}),
            'nombre_original': forms.TextInput(attrs={'style': INPUT, 'placeholder': 'Nombre original del fabricante (si es distinto del español)'}),
            'nombre_en':       forms.TextInput(attrs={'style': INPUT, 'placeholder': 'Nombre en inglés (opcional)'}),
            'descripcion':     forms.Textarea(attrs={'style': TEXTAREA, 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nombre'].required = True
        self.fields['nombre_original'].required = False
        self.fields['nombre_en'].required = False
        self.fields['descripcion'].required = False


class PiezaForm(forms.ModelForm):
    """Formulario de pieza individual. Siempre se crea con es_ensamble=False
    (fijado en la vista) — el campo 'ensamble' solo indica a qué Baugruppe pertenece,
    o se deja vacío si es una pieza suelta."""

    class Meta:
        model = Pieza
        fields = [
            'ensamble',
            'nombre', 'nombre_original', 'nombre_en',
            'numero_parte', 'numero_posicion', 'especificacion',
            'cantidad_en_maquina', 'descripcion', 'ubicacion_en_maquina',
            'imagen_ubicacion', 'imagen_pieza',
            'stock_repuestos', 'stock_minimo_repuestos',
        ]
        widgets = {
            'ensamble':             forms.Select(attrs={'style': SELECT}),
            'nombre':               forms.TextInput(attrs={'style': INPUT, 'placeholder': 'Nombre en español'}),
            'nombre_original':      forms.TextInput(attrs={'style': INPUT, 'placeholder': 'Nombre original del fabricante (si es distinto del español)'}),
            'nombre_en':            forms.TextInput(attrs={'style': INPUT, 'placeholder': 'Nombre en inglés (opcional)'}),
            'numero_parte':         forms.TextInput(attrs={'style': INPUT, 'placeholder': 'Código o número de parte del fabricante'}),
            'numero_posicion':      forms.NumberInput(attrs={'style': INPUT, 'placeholder': 'Pos. en diagrama del manual'}),
            'especificacion':       forms.TextInput(attrs={'style': INPUT, 'placeholder': 'Ej: M8xP1.25x20L'}),
            'cantidad_en_maquina':  forms.NumberInput(attrs={'style': INPUT, 'step': '0.01', 'min': '0'}),
            'descripcion':          forms.Textarea(attrs={'style': TEXTAREA, 'rows': 3}),
            'ubicacion_en_maquina': forms.TextInput(attrs={'style': INPUT, 'placeholder': 'Dónde está físicamente en la máquina'}),
            'stock_repuestos':      forms.NumberInput(attrs={'style': INPUT, 'min': '0'}),
            'stock_minimo_repuestos': forms.NumberInput(attrs={'style': INPUT, 'min': '0'}),
        }

    def __init__(self, *args, maquina=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo mostrar ensambles de la misma máquina
        if maquina:
            self.fields['ensamble'].queryset = Pieza.objects.filter(
                maquina=maquina, es_ensamble=True, activo=True
            )
        self.fields['ensamble'].empty_label = '— Sin ensamble (pieza suelta) —'
        self.fields['ensamble'].required = False
        self.fields['nombre'].required = True
        for fname in ['nombre_original', 'nombre_en', 'numero_parte', 'numero_posicion',
                      'especificacion', 'descripcion', 'ubicacion_en_maquina',
                      'imagen_ubicacion', 'imagen_pieza']:
            self.fields[fname].required = False


class CodigoParadaForm(forms.ModelForm):

    class Meta:
        model  = CodigoParada
        fields = [
            'fabricante', 'modelo_maquina', 'codigo',
            'tipo', 'categoria', 'subsistema', 'causa_raiz_comun',
        ]
        widgets = {
            'fabricante':      forms.TextInput(attrs={'style': INPUT, 'placeholder': 'Nombre del fabricante'}),
            'modelo_maquina':  forms.TextInput(attrs={'style': INPUT, 'placeholder': 'Modelo de la máquina'}),
            'codigo':          forms.TextInput(attrs={'style': INPUT, 'placeholder': 'Ej: PP01 / PNP-M01'}),
            'tipo':            forms.Select(attrs={'style': SELECT}),
            'categoria':       forms.Select(attrs={'style': SELECT}),
            'subsistema':      forms.TextInput(attrs={'style': INPUT, 'placeholder': 'Subsistema o componente afectado'}),
            'causa_raiz_comun': forms.Textarea(attrs={
                'style': TEXTAREA, 'rows': 3,
                'placeholder': 'Descripción técnica de la causa raíz más frecuente (opcional)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['causa_raiz_comun'].required = False

        # Poblar datalists con valores ya existentes para facilitar la entrada
        fabricantes  = CodigoParada.objects.values_list('fabricante', flat=True).distinct().order_by('fabricante')
        modelos      = CodigoParada.objects.values_list('modelo_maquina', flat=True).distinct().order_by('modelo_maquina')
        self.fabricantes_existentes = list(fabricantes)
        self.modelos_existentes     = list(modelos)


class TransferenciaPiezaForm(forms.ModelForm):

    ensamble_destino = forms.ModelChoiceField(
        queryset=Pieza.objects.none(),
        required=False,
        label='Asignar a ensamble en destino',
    )

    class Meta:
        model = TransferenciaPieza
        fields = ['maquina_destino', 'motivo', 'observaciones']
        widgets = {
            'maquina_destino': forms.Select(attrs={'style': SELECT}),
            'motivo':          forms.Textarea(attrs={'style': TEXTAREA, 'rows': 3, 'placeholder': 'Razón de la transferencia'}),
            'observaciones':   forms.Textarea(attrs={'style': TEXTAREA, 'rows': 2, 'placeholder': 'Observaciones adicionales (opcional)'}),
        }

    def __init__(self, *args, pieza=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Excluir la máquina origen del selector de destino
        qs = Maquina.objects.exclude(estado='FUERA_SERVICIO')
        if pieza:
            qs = qs.exclude(pk=pieza.maquina.pk)
        self.fields['maquina_destino'].queryset = qs
        self.fields['maquina_destino'].empty_label = '— Seleccionar máquina destino —'
        self.fields['maquina_destino'].required = True
        self.fields['motivo'].required = True
        self.fields['observaciones'].required = False

        # Una pieza individual puede engancharse a un ensamble ya existente en cualquiera
        # de las máquinas destino posibles; un ensamble en sí no tiene "ensamble padre".
        if pieza and not pieza.es_ensamble:
            self.fields['ensamble_destino'].queryset = Pieza.objects.filter(
                maquina__in=qs, es_ensamble=True, activo=True
            ).select_related('maquina').order_by('maquina__codigo', 'nombre')
            self.fields['ensamble_destino'].empty_label = '— Sin ensamble (pieza suelta) —'
        else:
            del self.fields['ensamble_destino']

    def clean(self):
        cleaned = super().clean()
        destino = cleaned.get('maquina_destino')
        ensamble_destino = cleaned.get('ensamble_destino')
        if ensamble_destino and destino and ensamble_destino.maquina_id != destino.pk:
            raise forms.ValidationError(
                'El ensamble seleccionado no pertenece a la máquina destino elegida.'
            )
        return cleaned