from django.db import models

from maquinas.models import Maquina
from usuarios.models import Usuario


class InspeccionTPM(models.Model):

    ESTADOS = [
        ('OK', 'Correcto'),
        ('OBSERVACION', 'Con Observaciones'),
        ('CRITICO', 'Crítico'),
    ]

    maquina = models.ForeignKey(
        Maquina,
        on_delete=models.CASCADE,
        related_name='inspecciones_tpm'
    )

    inspector = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True
    )

    fecha = models.DateField()

    limpieza = models.BooleanField(default=True)

    lubricacion = models.BooleanField(default=True)

    ajuste = models.BooleanField(default=True)

    observaciones = models.TextField(
        blank=True
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='OK'
    )

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.maquina.nombre} - {self.fecha}"


class IndicadorTPM(models.Model):

    maquina = models.ForeignKey(
        Maquina,
        on_delete=models.CASCADE,
        related_name='indicadores_tpm'
    )

    mes = models.PositiveIntegerField()

    anio = models.PositiveIntegerField()

    disponibilidad = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    rendimiento = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    calidad = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    oee = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        editable=False
    )

    def save(self, *args, **kwargs):

        self.oee = (
            self.disponibilidad *
            self.rendimiento *
            self.calidad
        ) / 10000

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.maquina.nombre} - {self.mes}/{self.anio}"


class HallazgoTPM(models.Model):

    PRIORIDADES = [
        ('BAJA', 'Baja'),
        ('MEDIA', 'Media'),
        ('ALTA', 'Alta'),
        ('CRITICA', 'Crítica'),
    ]

    inspeccion = models.ForeignKey(
        InspeccionTPM,
        on_delete=models.CASCADE,
        related_name='hallazgos'
    )

    descripcion = models.TextField()

    prioridad = models.CharField(
        max_length=20,
        choices=PRIORIDADES
    )

    resuelto = models.BooleanField(
        default=False
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.descripcion[:50]


