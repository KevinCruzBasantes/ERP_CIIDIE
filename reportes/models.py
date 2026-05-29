from django.db import models

from usuarios.models import Usuario


class ReporteGenerado(models.Model):

    TIPOS = [
        ('INVENTARIO', 'Inventario'),
        ('MANTENIMIENTO', 'Mantenimiento'),
        ('RESERVAS', 'Reservas'),
        ('TPM', 'TPM'),
    ]

    tipo = models.CharField(
        max_length=30,
        choices=TIPOS
    )

    generado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True
    )

    fecha_generacion = models.DateTimeField(
        auto_now_add=True
    )

    observaciones = models.TextField(
        blank=True
    )

    def __str__(self):
        return f"{self.tipo} - {self.fecha_generacion}"