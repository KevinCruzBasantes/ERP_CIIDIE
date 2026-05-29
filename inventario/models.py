from django.db import models


class Material(models.Model):

    TIPOS = [
        ('MADERA', 'Madera'),
        ('HERRAMIENTA', 'Herramienta'),
        ('CONSUMIBLE', 'Consumible'),
        ('REPUESTO', 'Repuesto'),
        ('OTRO', 'Otro'),
    ]

    codigo = models.CharField(
        max_length=20,
        unique=True
    )

    nombre = models.CharField(
        max_length=150
    )

    tipo = models.CharField(
        max_length=20,
        choices=TIPOS
    )

    descripcion = models.TextField(
        blank=True
    )

    stock_actual = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    stock_minimo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    unidad_medida = models.CharField(
        max_length=20,
        default='unidad'
    )

    costo_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    activo = models.BooleanField(
        default=True
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    @property
    def stock_bajo(self):
        return self.stock_actual <= self.stock_minimo


class ConsumoMaterial(models.Model):

    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name='consumos'
    )

    cantidad = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    observacion = models.TextField(
        blank=True
    )

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.material.nombre} - {self.cantidad}"

    def save(self, *args, **kwargs):

        if not self.pk:
            self.material.stock_actual -= self.cantidad
            self.material.save()

        super().save(*args, **kwargs)