from django.db import models
from django.core.exceptions import ValidationError

from maquinas.models import Maquina
from usuarios.models import Usuario


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
        related_name='mantenimientos'
    )

    tipo = models.CharField(
        max_length=20,
        choices=TIPOS
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='PROGRAMADO'
    )

    prioridad = models.CharField(
        max_length=20,
        choices=PRIORIDADES,
        default='MEDIA'
    )

    fecha_programada = models.DateField()

    fecha_inicio = models.DateTimeField(
        null=True,
        blank=True
    )

    fecha_fin = models.DateTimeField(
        null=True,
        blank=True
    )

    proxima_fecha = models.DateField(
        null=True,
        blank=True,
        help_text="Próxima fecha programada de mantenimiento"
    )

    descripcion = models.TextField()

    acciones_realizadas = models.TextField(
        blank=True
    )

    horas_trabajo = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0
    )

    costo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    observaciones = models.TextField(
        blank=True
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True
    )

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
        from django.utils import timezone

        return (
            self.estado != 'FINALIZADO'
            and self.fecha_programada < timezone.now().date()
        )

    def __str__(self):
        return (
            f"{self.maquina.nombre} - "
            f"{self.get_tipo_display()} - "
            f"{self.fecha_programada}"
        )