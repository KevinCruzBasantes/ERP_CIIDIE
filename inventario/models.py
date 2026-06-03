from django.db import models

from usuarios.models import Usuario


class Material(models.Model):

    # Tipos según requerimientos: mantenimiento / producción / ambos
    TIPOS = [
        ('MANTENIMIENTO', 'Mantenimiento'),
        ('PRODUCCION', 'Producción'),
        ('AMBOS', 'Ambos (Mantenimiento y Producción)'),
    ]

    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=150)

    tipo = models.CharField(
        max_length=20,
        choices=TIPOS,
        help_text="Clasificación según uso: mantenimiento, producción o ambos"
    )

    descripcion = models.TextField(blank=True)
    proveedor = models.CharField(max_length=200, blank=True)

    stock_actual = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    stock_minimo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Nivel mínimo — el sistema genera alerta cuando se alcanza"
    )
    unidad_medida = models.CharField(max_length=20, default='unidad')
    costo_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Material'
        verbose_name_plural = 'Materiales'

    def __str__(self):
        return f"{self.codigo} — {self.nombre}"

    @property
    def stock_bajo(self):
        return self.stock_actual <= self.stock_minimo


class ConsumoMaterial(models.Model):
    """
    Registra cada consumo de material vinculado a una orden de trabajo.
    El descuento de stock ocurre automáticamente al guardar.
    """

    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name='consumos'
    )

    # FK a OrdenTrabajo importada aquí con string para evitar import circular
    orden_trabajo = models.ForeignKey(
        'reservas.OrdenTrabajo',
        on_delete=models.CASCADE,
        related_name='consumos_material',
        null=True,
        blank=True,
        help_text="Orden de trabajo a la que se asocia este consumo"
    )

    realizado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consumos_registrados'
    )

    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)
    observacion = models.TextField(blank=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Consumo de material'
        verbose_name_plural = 'Consumos de materiales'

    def __str__(self):
        return f"{self.material.nombre} — {self.cantidad} {self.material.unidad_medida}"

    def save(self, *args, **kwargs):
        # Descontar del stock solo al crear (no en ediciones)
        if not self.pk:
            self.material.stock_actual -= self.cantidad
            self.material.save(update_fields=['stock_actual'])
        super().save(*args, **kwargs)