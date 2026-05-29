from django.db import models


class Maquina(models.Model):

    ESTADOS = [
        ('OPERATIVA', 'Operativa'),
        ('MANTENIMIENTO', 'Mantenimiento'),
        ('FUERA_SERVICIO', 'Fuera de servicio'),
    ]

    nombre = models.CharField(max_length=150)
    codigo = models.CharField(max_length=50, unique=True)

    descripcion = models.TextField(blank=True)

    ubicacion = models.CharField(max_length=200)

    fabricante = models.CharField(max_length=100, blank=True)

    modelo = models.CharField(max_length=100, blank=True)

    numero_serie = models.CharField(max_length=100, blank=True)

    fecha_adquisicion = models.DateField(null=True, blank=True)

    estado = models.CharField(
        max_length=30,
        choices=ESTADOS,
        default='OPERATIVA'
    )

    imagen = models.ImageField(
        upload_to='maquinas/',
        blank=True,
        null=True
    )

    manual_pdf = models.FileField(
        upload_to='manuales/',
        blank=True,
        null=True
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Pieza(models.Model):

    maquina = models.ForeignKey(
        Maquina,
        on_delete=models.CASCADE,
        related_name='piezas'
    )

    nombre = models.CharField(max_length=150)

    codigo = models.CharField(max_length=50)

    descripcion = models.TextField(blank=True)

    stock = models.PositiveIntegerField(default=0)

    ubicacion = models.CharField(max_length=200)

    imagen = models.ImageField(
        upload_to='piezas/',
        blank=True,
        null=True
    )

    def __str__(self):
        return self.nombre


class TransferenciaPieza(models.Model):

    pieza = models.ForeignKey(Pieza, on_delete=models.CASCADE)

    origen = models.CharField(max_length=200)

    destino = models.CharField(max_length=200)

    fecha = models.DateTimeField(auto_now_add=True)

    observaciones = models.TextField(blank=True)

    def __str__(self):
        return f"{self.pieza} -> {self.destino}"