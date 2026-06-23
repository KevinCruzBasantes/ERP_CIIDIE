from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from maquinas.models import Maquina
from usuarios.models import Usuario


# ─────────────────────────────────────────────────────────────────────────────
# Orden de trabajo de mantenimiento — documento formal para el técnico
# Inspirado en el sistema DANEC (Access): tabOrden
# Independiente de reservas; puede existir sin que haya una reserva activa.
# ─────────────────────────────────────────────────────────────────────────────
class OrdenMantenimiento(models.Model):

    TIPOS = [
        ('PREVENTIVO', 'Preventivo'),
        ('CORRECTIVO', 'Correctivo'),
    ]

    ESTADOS = [
        ('PROGRAMADA', 'Programada'),
        ('EN_PROCESO', 'En proceso'),
        ('FINALIZADA', 'Finalizada'),
        ('CANCELADA', 'Cancelada'),
    ]

    PRIORIDADES = [
        ('BAJA', 'Baja'),
        ('MEDIA', 'Media'),
        ('ALTA', 'Alta'),
        ('CRITICA', 'Crítica'),
    ]

    ORIGENES = [
        ('MANUAL', 'Creación manual'),
        ('INCIDENTE', 'Incidente'),
        ('PLAN', 'Plan de mantenimiento'),
        ('INSPECCION', 'Inspección diaria reprobada'),
        ('HALLAZGO', 'Hallazgo de inspección autónoma'),
        ('PARADA', 'Parada no planificada'),
        ('ESTADO_MAQUINA', 'Cambio de estado de máquina'),
        ('BITACORA', 'Bitácora de operario — requiere atención'),
    ]

    maquina = models.ForeignKey(
        Maquina,
        on_delete=models.CASCADE,
        related_name='ordenes_mantenimiento'
    )
    plan = models.ForeignKey(
        'PlanMantenimiento',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ordenes',
        help_text="Plan que originó esta orden (preventivos)"
    )
    incidente = models.ForeignKey(
        'tpm.Incidente',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ordenes_generadas',
        help_text="Incidente que originó esta orden (correctivos)"
    )
    inspeccion = models.ForeignKey(
        'tpm.InspeccionDiaria',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ordenes_generadas',
        help_text="Inspección diaria reprobada que originó esta orden"
    )
    hallazgo = models.ForeignKey(
        'tpm.HallazgoInspeccion',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ordenes_generadas',
        help_text="Hallazgo de inspección autónoma (Pilar 1 TPM) que originó esta orden"
    )
    parada = models.ForeignKey(
        'reservas.RegistroParada',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ordenes_generadas',
        help_text="Parada no planificada que originó esta orden"
    )
    bitacora_operario = models.ForeignKey(
        'reservas.BitacoraOperario',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ordenes_generadas',
        help_text="Entrada de bitácora de operario marcada como 'requiere atención' que originó esta orden"
    )
    origen = models.CharField(
        max_length=20,
        choices=ORIGENES,
        default='MANUAL',
        help_text="Disparador que generó esta orden"
    )
    creado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordenes_creadas'
    )

    tipo = models.CharField(max_length=20, choices=TIPOS, default='PREVENTIVO')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PROGRAMADA')
    prioridad = models.CharField(max_length=20, choices=PRIORIDADES, default='MEDIA')

    titulo = models.CharField(
        max_length=200,
        help_text="Descripción breve de lo que se debe hacer"
    )
    descripcion_tarea = models.TextField(
        blank=True,
        help_text="Procedimiento detallado, pasos a seguir"
    )

    # Hasta 3 responsables como en DANEC
    responsable_1 = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='om_responsable_1',
        verbose_name='Responsable principal'
    )
    responsable_2 = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='om_responsable_2',
        verbose_name='Responsable 2'
    )
    responsable_3 = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='om_responsable_3',
        verbose_name='Responsable 3'
    )

    fecha_programada = models.DateField()
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    tiempo_estimado_horas = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )

    repuestos_necesarios = models.TextField(
        blank=True,
        help_text="Lista de repuestos y materiales necesarios"
    )
    acciones_realizadas = models.TextField(blank=True)
    observaciones = models.TextField(blank=True)

    # Flags de impacto (como DANEC: bolAfectaseguridad, bolParada)
    afecta_seguridad = models.BooleanField(
        default=False,
        help_text="La falla o tarea representa un riesgo de seguridad"
    )
    para_produccion = models.BooleanField(
        default=False,
        help_text="La máquina queda fuera de servicio durante la intervención"
    )

    costo = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Visto bueno del supervisor (como txtVistoBueno en DANEC)
    autorizado_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='om_autorizadas',
        verbose_name='Visto bueno / Autorizado por'
    )
    fecha_autorizacion = models.DateTimeField(null=True, blank=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['-fecha_programada', '-fecha_creacion']
        verbose_name = 'Orden de mantenimiento'
        verbose_name_plural = 'Órdenes de mantenimiento'

    def numero(self):
        return f"OM-{self.pk:04d}"

    def __str__(self):
        return f"{self.numero()} — {self.maquina.codigo} — {self.titulo}"


# ─────────────────────────────────────────────────────────────────────────────
# Bitácora de mantenimiento — historial a nivel de máquina
# Inspirado en DANEC: tabBitacora (ligada a tabEquipo, no a tabOrden)
# Permite ver TODO lo que se ha hecho a una máquina en un solo lugar.
# ─────────────────────────────────────────────────────────────────────────────
class BitacoraMantenimiento(models.Model):

    maquina = models.ForeignKey(
        Maquina,
        on_delete=models.CASCADE,
        related_name='bitacora_mantenimiento',
        help_text="La máquina a la que pertenece este registro"
    )
    orden = models.ForeignKey(
        OrdenMantenimiento,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='entradas_bitacora',
        help_text="Orden de trabajo asociada (opcional)"
    )
    tecnico = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bitacora_mantenimiento'
    )

    fecha_registro = models.DateTimeField(auto_now_add=True)
    descripcion = models.TextField(
        help_text="Qué se realizó: trabajo ejecutado, hallazgos, resultados"
    )
    observaciones = models.TextField(blank=True)
    repuestos_utilizados = models.TextField(
        blank=True,
        help_text="Repuestos y materiales que se usaron efectivamente"
    )
    requiere_atencion = models.BooleanField(
        default=False,
        help_text="Marcar si el ingeniero debe revisar algo urgente"
    )
    foto = models.ImageField(
        upload_to='bitacora_mantenimiento/',
        null=True, blank=True
    )

    class Meta:
        ordering = ['-fecha_registro']
        verbose_name = 'Entrada de bitácora'
        verbose_name_plural = 'Bitácora de mantenimiento'

    def __str__(self):
        orden_str = self.orden.numero() if self.orden else 'Sin OT'
        return f"{self.maquina.codigo} — {orden_str} ({self.fecha_registro.strftime('%d/%m/%Y')})"


# ─────────────────────────────────────────────────────────────────────────────
# Plan de mantenimiento — plantilla periódica definida por el fabricante
# Separado del registro de ejecución (Mantenimiento).
#
# Ejemplo de la F210HSC (Wartungsplaner del manual):
#   - Lubricación guías lineales   → cada 8h de operación
#   - Verificación presión neumática → cada 40h (semanal)
#   - Cambio filtro refrigerante   → cada 500h
#   - Revisión husillo de bolas    → cada 2000h
# ─────────────────────────────────────────────────────────────────────────────
class PlanMantenimiento(models.Model):

    TIPOS_TPM = [
        ('P1_AUTONOMO', 'Pilar 1 — Autónomo (operador)'),
        ('P2_PREVENTIVO', 'Pilar 2 — Preventivo planificado'),
        ('P3_MEJORA', 'Pilar 3 — Mejora enfocada'),
        ('P7_SEGURIDAD', 'Pilar 7 — Seguridad'),
    ]

    UNIDADES_INTERVALO = [
        ('HORAS', 'Horas de operación'),
        ('DIAS', 'Días calendario'),
        ('SEMANAS', 'Semanas'),
        ('MESES', 'Meses'),
    ]

    maquina = models.ForeignKey(
        Maquina,
        on_delete=models.CASCADE,
        related_name='planes_mantenimiento'
    )

    nombre_tarea = models.CharField(
        max_length=200,
        help_text="Descripción breve de la tarea (ej: Lubricación guías lineales)"
    )
    descripcion_detallada = models.TextField(
        blank=True,
        help_text="Procedimiento paso a paso según el manual del fabricante"
    )

    tipo_tpm = models.CharField(
        max_length=20,
        choices=TIPOS_TPM,
        default='P2_PREVENTIVO'
    )

    # Intervalo: se usa uno de los dos (horas O días), no ambos
    intervalo_valor = models.PositiveIntegerField(
        help_text="Número de unidades entre cada mantenimiento (ej: 500)"
    )
    intervalo_unidad = models.CharField(
        max_length=10,
        choices=UNIDADES_INTERVALO,
        default='HORAS'
    )

    activo = models.BooleanField(
        default=True,
        help_text="Desactivar si la tarea ya no aplica a esta máquina"
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['maquina', 'intervalo_valor']
        verbose_name = 'Plan de mantenimiento'
        verbose_name_plural = 'Planes de mantenimiento'

    def __str__(self):
        return f"{self.maquina.codigo} — {self.nombre_tarea} (c/{self.intervalo_valor} {self.get_intervalo_unidad_display()})"


# ─────────────────────────────────────────────────────────────────────────────
# Registro de ejecución de mantenimiento
# Cada vez que se realiza (o programa) un mantenimiento se crea un registro.
# ─────────────────────────────────────────────────────────────────────────────
class Mantenimiento(models.Model):
    
    TIPOS = [
        ('PREVENTIVO', 'Preventivo'),
        ('CORRECTIVO', 'Correctivo'),
    ]

    ESTADOS = [
        ('PROGRAMADO', 'Programado'),
        ('EN_PROCESO', 'En Proceso'),
        ('FINALIZADO', 'Finalizado'),
        ('CANCELADO', 'Cancelado'),
    ]

    PRIORIDADES = [
        ('BAJA', 'Baja'),
        ('MEDIA', 'Media'),
        ('ALTA', 'Alta'),
        ('CRITICA', 'Crítica'),
    ]

    # Relación con el plan que originó este mantenimiento (opcional para correctivos)
    plan = models.ForeignKey(
        PlanMantenimiento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ejecuciones',
        help_text="Plan que originó este mantenimiento (vacío en correctivos no planificados)"
    )

    maquina = models.ForeignKey(
        Maquina,
        on_delete=models.CASCADE,
        related_name='mantenimientos'
    )

    responsable = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mantenimientos_realizados'
    )

    tipo = models.CharField(max_length=20, choices=TIPOS)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PROGRAMADO')
    prioridad = models.CharField(max_length=20, choices=PRIORIDADES, default='MEDIA')

    fecha_programada = models.DateField()
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)

    # Fecha calculada automáticamente para la próxima ejecución
    proxima_fecha = models.DateField(
        null=True,
        blank=True,
        help_text="Se calcula automáticamente al finalizar según el plan asociado"
    )

    descripcion = models.TextField(
        help_text="Qué se va a hacer / qué se hizo"
    )
    acciones_realizadas = models.TextField(blank=True)
    observaciones = models.TextField(blank=True)

    horas_trabajo = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    costo = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['-fecha_programada']
        verbose_name = 'Mantenimiento'
        verbose_name_plural = 'Mantenimientos'

    


    def clean(self):
        if self.fecha_inicio and self.fecha_fin:
            if self.fecha_fin < self.fecha_inicio:
                raise ValidationError(
                    "La fecha de fin no puede ser menor que la fecha de inicio."
                )

    @property
    def esta_vencido(self):
        return (
            self.estado not in ('FINALIZADO', 'CANCELADO')
            and self.fecha_programada < timezone.now().date()
        )

    @property
    def dias_para_vencer(self):
        delta = self.fecha_programada - timezone.now().date()
        return delta.days

    def __str__(self):
        return (
            f"{self.maquina.nombre} — "
            f"{self.get_tipo_display()} — "
            f"{self.fecha_programada}"
        )