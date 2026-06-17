from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from maquinas.models import Maquina, CodigoParada
from usuarios.models import Usuario


class Reserva(models.Model):

    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADA', 'Aprobada'),
        ('EN_USO', 'En uso'),
        ('COMPLETADA', 'Completada'),
        ('CANCELADA', 'Cancelada'),
    ]

    PROPOSITOS = [
        ('ENSENANZA', 'Enseñanza / Clase'),
        ('INVESTIGACION', 'Investigación / Tesis'),
        ('PRODUCCION', 'Producción'),
        ('PEDIDO_EXTERNO', 'Pedido externo'),
    ]

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reservas'
    )
    maquina = models.ForeignKey(
        Maquina,
        on_delete=models.CASCADE,
        related_name='reservas'
    )
    autorizador = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservas_autorizadas'
    )

    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    proposito = models.CharField(
        max_length=20,
        choices=PROPOSITOS,
        default='ENSENANZA'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='PENDIENTE'
    )
    observaciones = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-hora_inicio']
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'

    def clean(self):
        # Cancelar o completar (cerrar_orden) siempre debe poder hacerse, sin importar
        # si la máquina o la certificación del usuario cambiaron de estado después de
        # crear la reserva o de empezar a usar la máquina — revalidar esas condiciones
        # al cerrar el trabajo no tiene sentido (el trabajo ya se hizo) y antes rompía
        # cerrar_orden con un 500 si la certificación vencía a mitad de un trabajo largo.
        if self.estado in ('CANCELADA', 'COMPLETADA'):
            return
        if self.hora_fin <= self.hora_inicio:
            raise ValidationError(
                "La hora de fin debe ser mayor que la hora de inicio."
            )
        # Verificar que la máquina esté operativa
        if self.maquina and self.maquina.estado != 'OPERATIVA':
            raise ValidationError(
                f"La máquina '{self.maquina.nombre}' no está operativa "
                f"(estado: {self.maquina.get_estado_display()})."
            )
        # Verificar conflicto de horario
        conflicto = Reserva.objects.filter(
            maquina=self.maquina,
            fecha=self.fecha,
            estado__in=('PENDIENTE', 'APROBADA', 'EN_USO'),
            hora_inicio__lt=self.hora_fin,
            hora_fin__gt=self.hora_inicio,
        ).exclude(pk=self.pk)
        if conflicto.exists():
            raise ValidationError(
                "La máquina ya tiene una reserva en ese horario."
            )
        # Verificar certificación vigente (Pilar 4 TPM — Formación)
        if self.usuario_id and self.maquina_id:
            from tpm.models import CertificacionUsuario
            tiene_certificacion = CertificacionUsuario.objects.filter(
                usuario_id=self.usuario_id,
                maquina_id=self.maquina_id,
                activo=True,
                fecha_vencimiento__gte=timezone.now().date(),
            ).exists()
            if not tiene_certificacion:
                raise ValidationError(
                    f"{self.usuario} no tiene una certificación vigente para operar "
                    f"'{self.maquina.nombre}'. Solicita la certificación antes de reservar esta máquina."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        usuario_str = self.usuario.username if self.usuario else '— usuario eliminado —'
        return f"{usuario_str} — {self.maquina.nombre} ({self.fecha})"


class OrdenTrabajo(models.Model):

    ESTADOS = [
        ('ABIERTA', 'Abierta'),
        ('EN_PROCESO', 'En Proceso'),
        ('FINALIZADA', 'Finalizada'),
        ('CANCELADA', 'Cancelada'),
    ]

    reserva = models.OneToOneField(
        Reserva,
        on_delete=models.CASCADE,
        related_name='orden_trabajo'
    )

    descripcion = models.TextField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='ABIERTA')

    # ── Campos para cálculo OEE ───────────────────────────────────────
    tiempo_planificado_min = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
        help_text="Tiempo de carga / planificado en minutos"
    )
    tiempo_real_min = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Tiempo real de operación en minutos"
    )
    tiempo_parada_min = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
        help_text="Tiempo total de paradas no planificadas en minutos"
    )
    unidades_producidas = models.PositiveIntegerField(
        default=0,
        help_text="Para cálculo de Rendimiento OEE"
    )
    unidades_esperadas = models.PositiveIntegerField(
        default=0,
        help_text="Producción teórica esperada"
    )
    unidades_sin_defecto = models.PositiveIntegerField(
        default=0,
        help_text="Unidades aprobadas (para cálculo de Calidad OEE)"
    )

    resultado = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Orden de trabajo'
        verbose_name_plural = 'Órdenes de trabajo'

    def __str__(self):
        return f"OT-{self.pk:04d}"


# ─────────────────────────────────────────────────────────────────────────────
# Registro de paradas vinculadas a una orden de trabajo
# Cada parada referencia un CodigoParada del catálogo del modelo de máquina
# ─────────────────────────────────────────────────────────────────────────────
class RegistroParada(models.Model):

    orden_trabajo = models.ForeignKey(
        OrdenTrabajo,
        on_delete=models.CASCADE,
        related_name='paradas'
    )
    codigo_parada = models.ForeignKey(
        CodigoParada,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registros',
        help_text="Código del catálogo del modelo de máquina"
    )

    hora_inicio = models.TimeField()
    hora_fin = models.TimeField(null=True, blank=True)
    duracion_minutos = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True
    )

    descripcion_tecnica = models.TextField(
        help_text="Descripción técnica / observaciones del operario sobre la parada"
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['orden_trabajo', 'hora_inicio']
        verbose_name = 'Registro de parada'
        verbose_name_plural = 'Registros de paradas'

    def save(self, *args, **kwargs):
        # Calcular duración automáticamente si se tienen ambas horas
        if self.hora_inicio and self.hora_fin:
            from datetime import datetime, date
            inicio = datetime.combine(date.today(), self.hora_inicio)
            fin = datetime.combine(date.today(), self.hora_fin)
            self.duracion_minutos = (fin - inicio).seconds / 60
        super().save(*args, **kwargs)

    def __str__(self):
        codigo = self.codigo_parada.codigo if self.codigo_parada else 'Sin código'
        return f"{self.orden_trabajo} — [{codigo}] {self.hora_inicio}"


# ─────────────────────────────────────────────────────────────────────────────
# Bitácora del operario — texto libre estructurado por orden de trabajo
# Separado de OrdenTrabajo para que el operario pueda registrar
# múltiples entradas durante la ejecución
# ─────────────────────────────────────────────────────────────────────────────
class BitacoraOperario(models.Model):

    orden_trabajo = models.ForeignKey(
        OrdenTrabajo,
        on_delete=models.CASCADE,
        related_name='entradas_bitacora'
    )
    operario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        related_name='entradas_bitacora'
    )

    fecha_registro = models.DateTimeField(auto_now_add=True)
    descripcion_trabajo = models.TextField(
        help_text="Qué se realizó en esta entrada"
    )
    observaciones = models.TextField(blank=True)
    requiere_atencion = models.BooleanField(
        default=False,
        help_text="Marcar si hay algo que el ingeniero debe revisar"
    )
    foto = models.ImageField(
        upload_to='bitacora/',
        blank=True,
        null=True
    )

    class Meta:
        ordering = ['orden_trabajo', 'fecha_registro']
        verbose_name = 'Entrada de bitácora'
        verbose_name_plural = 'Bitácora del operario'

    def __str__(self):
        return f"{self.orden_trabajo} — {self.operario} ({self.fecha_registro.strftime('%d/%m/%Y %H:%M')})"