from django import forms
from .models import Mantenimiento, PlanMantenimiento, OrdenMantenimiento, BitacoraMantenimiento
from maquinas.models import Maquina
from usuarios.models import Usuario

FIELD_STYLE    = 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none;'
SELECT_STYLE   = 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.88rem; outline:none; cursor:pointer;'
TEXTAREA_STYLE = 'width:100%; padding:0.65rem 0.9rem; background:#1e2333; border:1px solid #2a2f42; border-radius:6px; color:#d4d8e8; font-size:0.85rem; outline:none; resize:vertical;'


class PlanMantenimientoForm(forms.ModelForm):

    class Meta:
        model  = PlanMantenimiento
        fields = [
            'maquina', 'nombre_tarea', 'descripcion_detallada',
            'tipo_tpm',
            'intervalo_dias', 'ultima_ejecucion_fecha',
            'intervalo_horas', 'ultima_ejecucion_horas',
            'activo',
        ]
        widgets = {
            'maquina':                forms.Select(attrs={'style': SELECT_STYLE}),
            'nombre_tarea':           forms.TextInput(attrs={
                'style': FIELD_STYLE,
                'placeholder': 'Ej: Lubricación guías lineales',
            }),
            'descripcion_detallada':  forms.Textarea(attrs={
                'style': TEXTAREA_STYLE, 'rows': 4,
                'placeholder': 'Procedimiento paso a paso según el manual del fabricante',
            }),
            'tipo_tpm':               forms.Select(attrs={'style': SELECT_STYLE}),
            'intervalo_dias':         forms.NumberInput(attrs={
                'style': FIELD_STYLE, 'min': '1', 'placeholder': 'Ej: 30',
            }),
            'ultima_ejecucion_fecha': forms.DateInput(attrs={
                'style': FIELD_STYLE, 'type': 'date',
            }),
            'intervalo_horas':        forms.NumberInput(attrs={
                'style': FIELD_STYLE, 'min': '1', 'placeholder': 'Ej: 500',
            }),
            'ultima_ejecucion_horas': forms.NumberInput(attrs={
                'style': FIELD_STYLE, 'min': '0', 'step': '0.01',
                'placeholder': 'Ej: 0 (si es la primera vez)',
            }),
            'activo': forms.CheckboxInput(attrs={'style': 'width:1rem; height:1rem; cursor:pointer;'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['maquina'].queryset = Maquina.objects.all().order_by('nombre')
        self.fields['descripcion_detallada'].required = False
        self.fields['intervalo_dias'].required = False
        self.fields['intervalo_horas'].required = False
        self.fields['ultima_ejecucion_fecha'].required = False
        self.fields['ultima_ejecucion_horas'].required = False

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('intervalo_dias') and not cleaned.get('intervalo_horas'):
            raise forms.ValidationError(
                'Debes definir al menos un disparador: intervalo en días o en horas de operación.'
            )
        return cleaned


class MantenimientoForm(forms.ModelForm):

    class Meta:
        model  = Mantenimiento
        fields = [
            'maquina', 'plan', 'responsable', 'tipo', 'estado',
            'prioridad', 'fecha_programada', 'fecha_inicio', 'fecha_fin',
            'proxima_fecha', 'descripcion', 'acciones_realizadas',
            'observaciones', 'horas_trabajo', 'costo',
        ]
        widgets = {
            'maquina':          forms.Select(attrs={'style': SELECT_STYLE}),
            'plan':             forms.Select(attrs={'style': SELECT_STYLE}),
            'responsable':      forms.Select(attrs={'style': SELECT_STYLE}),
            'tipo':             forms.Select(attrs={'style': SELECT_STYLE}),
            'estado':           forms.Select(attrs={'style': SELECT_STYLE}),
            'prioridad':        forms.Select(attrs={'style': SELECT_STYLE}),
            'fecha_programada': forms.DateInput(
                attrs={'style': FIELD_STYLE, 'type': 'date'},
                format='%Y-%m-%d'
            ),
            'proxima_fecha':    forms.DateInput(
                attrs={'style': FIELD_STYLE, 'type': 'date'},
                format='%Y-%m-%d'
            ),
            'fecha_inicio':     forms.DateTimeInput(
                attrs={'style': FIELD_STYLE, 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'fecha_fin':        forms.DateTimeInput(
                attrs={'style': FIELD_STYLE, 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'descripcion':      forms.Textarea(attrs={
                'style': TEXTAREA_STYLE, 'rows': 3,
                'placeholder': 'Describe el trabajo a realizar o realizado'
            }),
            'acciones_realizadas': forms.Textarea(attrs={'style': TEXTAREA_STYLE, 'rows': 3}),
            'observaciones':    forms.Textarea(attrs={'style': TEXTAREA_STYLE, 'rows': 2}),
            'horas_trabajo':    forms.NumberInput(attrs={'style': FIELD_STYLE, 'step': '0.01', 'placeholder': '0.00'}),
            'costo':            forms.NumberInput(attrs={'style': FIELD_STYLE, 'step': '0.01', 'placeholder': '0.00'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['maquina'].queryset     = Maquina.objects.all().order_by('nombre')
        self.fields['plan'].queryset        = PlanMantenimiento.objects.filter(
            activo=True
        ).select_related('maquina').order_by('maquina__nombre')
        self.fields['plan'].empty_label     = '— Sin plan asociado (correctivo) —'
        self.fields['responsable'].queryset = Usuario.objects.filter(
            estado='ACTIVO'
        ).exclude(is_superuser=True).order_by('first_name')
        self.fields['responsable'].empty_label = '— Sin responsable asignado —'

        # Campos opcionales
        self.fields['fecha_inicio'].required      = False
        self.fields['fecha_fin'].required         = False
        self.fields['proxima_fecha'].required     = False
        self.fields['plan'].required              = False
        self.fields['responsable'].required       = False
        self.fields['acciones_realizadas'].required = False
        self.fields['observaciones'].required     = False

        # Campos requeridos
        self.fields['descripcion'].required      = True
        self.fields['maquina'].required          = True
        self.fields['fecha_programada'].required = True

        # Formatos de entrada para que los valores existentes se muestren al editar
        self.fields['fecha_programada'].input_formats = ['%Y-%m-%d']
        self.fields['proxima_fecha'].input_formats    = ['%Y-%m-%d']
        self.fields['fecha_inicio'].input_formats     = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M']
        self.fields['fecha_fin'].input_formats        = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M']


class OrdenMantenimientoForm(forms.ModelForm):

    class Meta:
        model  = OrdenMantenimiento
        # Un solo responsable por orden (decisión 2026-07-13): responsable_2/3
        # siguen en el modelo por compatibilidad histórica/estilo DANEC, pero ya
        # no se ofrecen en el formulario — la asignación es individual, igual que
        # el botón "Asignarme la orden".
        fields = [
            'maquina', 'plan', 'tipo', 'prioridad', 'titulo',
            'descripcion_tarea', 'responsable_1',
            'fecha_programada', 'tiempo_estimado_horas',
            'repuestos_necesarios', 'afecta_seguridad', 'para_produccion',
        ]
        widgets = {
            'maquina':               forms.Select(attrs={'style': SELECT_STYLE}),
            'plan':                  forms.Select(attrs={'style': SELECT_STYLE}),
            'tipo':                  forms.Select(attrs={'style': SELECT_STYLE}),
            'prioridad':             forms.Select(attrs={'style': SELECT_STYLE}),
            'titulo':                forms.TextInput(attrs={
                'style': FIELD_STYLE,
                'placeholder': 'Ej: Cambio de filtro de refrigerante',
            }),
            'descripcion_tarea':     forms.Textarea(attrs={
                'style': TEXTAREA_STYLE, 'rows': 5,
                'placeholder': 'Pasos a seguir, herramientas necesarias, precauciones...',
            }),
            'responsable_1':         forms.Select(attrs={'style': SELECT_STYLE}),
            'fecha_programada':      forms.DateInput(
                attrs={'style': FIELD_STYLE, 'type': 'date'},
                format='%Y-%m-%d'
            ),
            'tiempo_estimado_horas': forms.NumberInput(attrs={
                'style': FIELD_STYLE, 'step': '0.5', 'min': '0',
                'placeholder': 'Ej: 2.0',
            }),
            'repuestos_necesarios':  forms.Textarea(attrs={
                'style': TEXTAREA_STYLE, 'rows': 3,
                'placeholder': 'Lista de repuestos y materiales necesarios',
            }),
            'afecta_seguridad':      forms.CheckboxInput(attrs={'style': 'width:1rem; height:1rem; cursor:pointer;'}),
            'para_produccion':       forms.CheckboxInput(attrs={'style': 'width:1rem; height:1rem; cursor:pointer;'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['maquina'].queryset      = Maquina.objects.all().order_by('nombre')
        self.fields['plan'].queryset         = PlanMantenimiento.objects.filter(activo=True).select_related('maquina').order_by('maquina__nombre')
        self.fields['plan'].empty_label      = '— Sin plan (correctivo) —'
        # Solo jerarquía alta (admin/PhD/técnico) puede ser responsable de una OM
        # (feedback testeo 2026-07-13) — el rol se muestra junto al nombre.
        from usuarios.permisos import es_admin_o_tecnico as _es_staff, filtrar_usuarios_por_rol
        candidatos = Usuario.objects.filter(estado='ACTIVO').exclude(is_superuser=True)
        tecnicos = filtrar_usuarios_por_rol(candidatos, _es_staff)
        if self.instance and self.instance.pk and self.instance.responsable_1_id:
            # Conservar al responsable ya asignado aunque el filtro lo excluyera
            tecnicos = (tecnicos | Usuario.objects.filter(pk=self.instance.responsable_1_id)).distinct()
        self.fields['responsable_1'].queryset = tecnicos.order_by('first_name', 'last_name')
        self.fields['responsable_1'].empty_label = '— Seleccionar —'
        self.fields['responsable_1'].label_from_instance = lambda u: (
            f"{u.get_full_name() or u.username} — {u.rol.nombre if u.rol else 'Sin rol'}"
        )
        # Opcionales
        self.fields['plan'].required              = False
        self.fields['descripcion_tarea'].required = False
        self.fields['responsable_1'].required     = False
        self.fields['tiempo_estimado_horas'].required = False
        self.fields['repuestos_necesarios'].required  = False
        self.fields['fecha_programada'].input_formats = ['%Y-%m-%d']


class BitacoraMantenimientoForm(forms.ModelForm):

    class Meta:
        model  = BitacoraMantenimiento
        fields = [
            'tipo_actividad', 'tiempo_horas',
            'descripcion', 'repuestos_utilizados', 'observaciones',
            'requiere_atencion', 'foto',
        ]
        widgets = {
            'tipo_actividad':      forms.Select(attrs={'style': SELECT_STYLE}),
            'tiempo_horas':        forms.NumberInput(attrs={
                'style': FIELD_STYLE, 'step': '0.25', 'min': '0',
                'placeholder': 'Ej: 1.5',
            }),
            'descripcion':         forms.Textarea(attrs={
                'style': TEXTAREA_STYLE, 'rows': 4,
                'placeholder': 'Qué se hizo, resultados, hallazgos...',
            }),
            'observaciones':       forms.Textarea(attrs={
                'style': TEXTAREA_STYLE, 'rows': 2,
                'placeholder': 'Notas adicionales',
            }),
            'repuestos_utilizados': forms.Textarea(attrs={
                'style': TEXTAREA_STYLE, 'rows': 2,
                'placeholder': 'Repuestos y materiales utilizados efectivamente',
            }),
            'requiere_atencion':   forms.CheckboxInput(attrs={'style': 'width:1rem; height:1rem; cursor:pointer;'}),
            'foto':                forms.FileInput(attrs={'style': 'color:#d4d8e8; font-size:0.82rem;'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo_actividad'].required      = False
        self.fields['tiempo_horas'].required        = False
        self.fields['observaciones'].required       = False
        self.fields['repuestos_utilizados'].required = False
        self.fields['foto'].required                = False
        self.fields['tipo_actividad'].empty_label   = '— Tipo de actividad —'