from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from maquinas.models import Maquina
from usuarios.models import Usuario


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