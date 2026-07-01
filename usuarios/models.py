from django.db import models
from django.contrib.auth.models import AbstractUser


class Rol(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Permiso(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Permiso'
        verbose_name_plural = 'Permisos'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Usuario(AbstractUser):

    ESTADOS = [
        ('ACTIVO', 'Activo'),
        ('INACTIVO', 'Inactivo'),
        ('SUSPENDIDO', 'Suspendido'),
    ]

    cedula = models.CharField(max_length=10, unique=True)
    telefono = models.CharField(max_length=20, blank=True)

    rol = models.ForeignKey(
        Rol,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios'
    )

    permisos_personalizados = models.ManyToManyField(
        Permiso,
        blank=True,
        related_name='usuarios'
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='ACTIVO'
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def esta_activo(self):
        return self.estado == 'ACTIVO'


class DisponibilidadOperador(models.Model):
    """Horario semanal recurrente que un operador declara para su propio
    trabajo. Se usa para filtrar qué operadores aparecen seleccionables al
    reservar según el día/hora de la reserva."""

    DIAS_SEMANA = [
        (0, 'Lunes'),
        (1, 'Martes'),
        (2, 'Miércoles'),
        (3, 'Jueves'),
        (4, 'Viernes'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]

    operador = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='disponibilidad'
    )
    dia_semana = models.IntegerField(choices=DIAS_SEMANA)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['dia_semana', 'hora_inicio']
        verbose_name = 'Disponibilidad de operador'
        verbose_name_plural = 'Disponibilidad de operadores'

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.hora_fin <= self.hora_inicio:
            raise ValidationError("La hora de fin debe ser mayor que la hora de inicio.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.operador} — {self.get_dia_semana_display()} {self.hora_inicio.strftime('%H:%M')}–{self.hora_fin.strftime('%H:%M')}"