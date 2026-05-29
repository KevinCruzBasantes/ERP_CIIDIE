from django.db import models
from django.core.exceptions import ValidationError

from maquinas.models import Maquina
from usuarios.models import Usuario


class Reserva(models.Model):

    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADA', 'Aprobada'),
        ('CANCELADA', 'Cancelada'),
        ('FINALIZADA', 'Finalizada'),
    ]

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='reservas'
    )

    maquina = models.ForeignKey(
        Maquina,
        on_delete=models.CASCADE,
        related_name='reservas'
    )

    fecha = models.DateField()

    hora_inicio = models.TimeField()

    hora_fin = models.TimeField()

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='PENDIENTE'
    )

    observaciones = models.TextField(
        blank=True
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-fecha', '-hora_inicio']

    def clean(self):

        if self.hora_fin <= self.hora_inicio:
            raise ValidationError(
                "La hora de fin debe ser mayor que la hora de inicio."
            )

        conflicto = Reserva.objects.filter(
            maquina=self.maquina,
            fecha=self.fecha,
            hora_inicio__lt=self.hora_fin,
            hora_fin__gt=self.hora_inicio
        ).exclude(pk=self.pk)

        if conflicto.exists():
            raise ValidationError(
                "La máquina ya está reservada en ese horario."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.usuario.username} - {self.maquina.nombre}"


class OrdenTrabajo(models.Model):

    ESTADOS = [
        ('ABIERTA', 'Abierta'),
        ('EN_PROCESO', 'En Proceso'),
        ('FINALIZADA', 'Finalizada'),
    ]

    reserva = models.OneToOneField(
        Reserva,
        on_delete=models.CASCADE,
        related_name='orden_trabajo'
    )

    descripcion = models.TextField()

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='ABIERTA'
    )

    tiempo_estimado_horas = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    tiempo_real_horas = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"OT-{self.id}"