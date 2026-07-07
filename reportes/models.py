from django.db import models

from usuarios.models import Usuario


class ReporteGenerado(models.Model):

    TIPOS = [
        ('RESUMEN', 'Resumen ejecutivo'),
        ('MANTENIMIENTO', 'Mantenimiento'),
        ('PRODUCCION', 'Producción y uso'),
        ('INVENTARIO', 'Inventario y piezas'),
        ('SEGURIDAD', 'Seguridad y personal'),
        ('BACKUP', 'Respaldo completo'),
    ]

    tipo = models.CharField(max_length=30, choices=TIPOS)

    generado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reportes_generados'
    )

    fecha_inicio_periodo = models.DateField(
        null=True, blank=True,
        help_text="Inicio del período analizado"
    )
    fecha_fin_periodo = models.DateField(
        null=True, blank=True,
        help_text="Fin del período analizado"
    )

    archivo = models.FileField(
        upload_to='reportes/',
        blank=True,
        null=True,
        help_text="Archivo Excel generado"
    )

    fecha_generacion = models.DateTimeField(auto_now_add=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ['-fecha_generacion']
        verbose_name = 'Reporte generado'
        verbose_name_plural = 'Reportes generados'

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.fecha_generacion.strftime('%d/%m/%Y %H:%M')}"