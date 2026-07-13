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
        from usuarios.permisos import es_admin, es_admin_o_tecnico, es_estudiante, filtrar_usuarios_por_rol
        self.usuario_actual = usuario_actual

        candidatos = Usuario.objects.filter(estado='ACTIVO').exclude(is_superuser=True)
        # Los estudiantes nunca operan la máquina por sí mismos (siempre delegan
        # en un operador certificado), así que no se los certifica (2026-07-13).
        candidatos = filtrar_usuarios_por_rol(candidatos, lambda u: not es_estudiante(u))
        if usuario_actual:
            candidatos = candidatos.exclude(pk=usuario_actual.pk)
            if not es_admin(usuario_actual):
                # Un tecnico (no admin) solo puede otorgar certificaciones a
                # perfiles inferiores (no a otro tecnico ni a un administrador).
                ids_permitidos = [u.pk for u in candidatos if not es_admin_o_tecnico(u)]
                candidatos = candidatos.filter(pk__in=ids_permitidos)

        # Al editar, conservar el usuario ya asignado entre las opciones aunque
        # el filtro de arriba normalmente lo hubiera excluido (p.ej. un tecnico
        # editando una certificacion que ya tenia asignada a otro tecnico).
        if self.instance.pk and self.instance.usuario_id:
            candidatos = candidatos | Usuario.objects.filter(pk=self.instance.usuario_id)

        # La certificación es personal: al editar no se puede cambiar de titular
        # (para otra persona se crea una certificación nueva). `disabled` hace que
        # Django ignore cualquier valor POSTeado y use el de la instancia.
        if self.instance.pk:
            self.fields['usuario'].disabled = True
            self.fields['usuario'].help_text = (
                'El titular no se puede cambiar; para certificar a otra persona crea una certificación nueva.'
            )

        self.fields['usuario'].queryset = candidatos.order_by('username')
        # Mostrar el rol junto al nombre para poder ubicar/filtrar por tipeo
        # tanto por nombre como por rol cuando haya muchos usuarios.
        self.fields['usuario'].label_from_instance = lambda u: (
            f"{u.get_full_name() or u.username} — {u.rol.nombre if u.rol else 'Sin rol'}"
        )
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

    # Separador interno del value del <select> (fabricante ||| modelo)
    SEP = '|||'

    # El ámbito ya no es texto libre: se elige entre los fabricante+modelo de
    # las máquinas registradas, porque la inspección diaria empareja los ítems
    # por texto EXACTO contra maquina.fabricante/maquina.modelo — un typo y el
    # ítem no aparecía nunca (feedback testeo 2026-07-13).
    ambito = forms.ChoiceField(
        widget=forms.Select(attrs={'style': SELECT_STYLE}),
        label='Fabricante y modelo',
    )

    class Meta:
        model  = ItemChecklistInspeccion
        fields = ['nombre', 'descripcion', 'es_critico', 'orden']
        widgets = {
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
        from maquinas.models import Maquina
        self.fields['descripcion'].required = False
        self.fields['orden'].required = False

        pares = (
            Maquina.objects.exclude(estado='BAJA')
            .values_list('fabricante', 'modelo')
            .distinct()
            .order_by('fabricante', 'modelo')
        )
        choices = [
            (f'{fab}{self.SEP}{mod}', f'{fab} — {mod}')
            for fab, mod in pares if (fab or mod)
        ]
        # Al editar, conservar el ámbito actual aunque ya no exista una máquina
        # con ese fabricante+modelo (p.ej. la máquina se dio de baja).
        if self.instance.pk:
            actual = f'{self.instance.fabricante}{self.SEP}{self.instance.modelo_maquina}'
            if actual not in dict(choices):
                choices.append((
                    actual,
                    f'{self.instance.fabricante} — {self.instance.modelo_maquina} (sin máquina registrada)',
                ))
            self.fields['ambito'].initial = actual
        self.fields['ambito'].choices = [('', '— Seleccionar fabricante y modelo —')] + choices

    def clean(self):
        cleaned = super().clean()
        ambito = cleaned.get('ambito')
        if ambito:
            fabricante, _, modelo = ambito.partition(self.SEP)
            self.instance.fabricante = fabricante
            self.instance.modelo_maquina = modelo
            # Validación manual del unique_together (fabricante, modelo, nombre):
            # como fabricante/modelo ya no son campos del form, validate_unique
            # no los cubre y sin esto el choque llegaría como IntegrityError.
            nombre = cleaned.get('nombre')
            if nombre:
                repetidos = ItemChecklistInspeccion.objects.filter(
                    fabricante=fabricante, modelo_maquina=modelo, nombre=nombre
                )
                if self.instance.pk:
                    repetidos = repetidos.exclude(pk=self.instance.pk)
                if repetidos.exists():
                    raise forms.ValidationError(
                        'Ya existe un ítem con ese texto para este fabricante y modelo.'
                    )
        return cleaned