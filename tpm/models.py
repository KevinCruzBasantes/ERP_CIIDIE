from django.db import models
from django.utils import timezone

from maquinas.models import Maquina
from usuarios.models import Usuario


# ─────────────────────────────────────────────────────────────────────────────
# Certificación de usuario por máquina (Pilar 4 TPM)
# Sin certificación vigente → el sistema bloquea la reserva
# ─────────────────────────────────────────────────────────────────────────────
class CertificacionUsuario(models.Model):

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        related_name='certificaciones'
    )
    maquina = models.ForeignKey(
        Maquina,
        on_delete=models.CASCADE,
        related_name='certificaciones'
    )
    otorgado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        related_name='certificaciones_otorgadas'
    )

    fecha_otorgamiento = models.DateField()
    fecha_vencimiento = models.DateField()
    observaciones = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['-fecha_vencimiento']
        # Un usuario tiene una certificación vigente por máquina a la vez
        unique_together = [['usuario', 'maquina', 'fecha_otorgamiento']]
        verbose_name = 'Certificación de usuario'
        verbose_name_plural = 'Certificaciones de usuarios'

    @property
    def vigente(self):
        return self.fecha_vencimiento >= timezone.now().date()

    @property
    def dias_para_vencer(self):
        return (self.fecha_vencimiento - timezone.now().date()).days

    def __str__(self):
        estado = "vigente" if self.vigente else "VENCIDA"
        usuario_str = self.usuario.username if self.usuario else '— usuario eliminado —'
        return f"{usuario_str} — {self.maquina.codigo} [{estado}]"


# ─────────────────────────────────────────────────────────────────────────────
# Catálogo de ítems de checklist específicos por fabricante+modelo
# (mismo patrón de scope que CodigoParada en maquinas/models.py).
# Cubre lo que NO es universal: niveles de aceite/refrigerante, presión
# neumática, etc. — cosas que solo aplican a ciertos tipos de máquina y
# cuyo rango/criterio depende del fabricante.
# ─────────────────────────────────────────────────────────────────────────────
class ItemChecklistInspeccion(models.Model):

    fabricante = models.CharField(
        max_length=100,
        help_text="Nombre del fabricante — el ítem aplica a todas las máquinas de este fabricante+modelo"
    )
    modelo_maquina = models.CharField(
        max_length=100,
        help_text="Modelo de la máquina"
    )

    nombre = models.CharField(
        max_length=200,
        help_text="Texto que verá el operario, incluyendo el criterio concreto del fabricante"
    )
    descripcion = models.TextField(
        blank=True,
        help_text="Detalle adicional o criterio de aceptación (opcional)"
    )
    es_critico = models.BooleanField(
        default=True,
        help_text="Si falla, la inspección completa queda como no aprobada"
    )
    orden = models.PositiveSmallIntegerField(
        default=0,
        help_text="Orden de aparición en el checklist"
    )
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['fabricante', 'modelo_maquina', 'orden', 'nombre']
        unique_together = [['fabricante', 'modelo_maquina', 'nombre']]
        verbose_name = 'Ítem de checklist'
        verbose_name_plural = 'Ítems de checklist'

    def __str__(self):
        return f"[{self.modelo_maquina}] {self.nombre}"


# ─────────────────────────────────────────────────────────────────────────────
# Inspección diaria (Pilar 1 TPM — Mantenimiento Autónomo)
# El operario llena este checklist ANTES de usar la máquina.
# Si aprobada=False → se genera una Alerta automáticamente y la máquina
# queda bloqueada para reservas ese día.
#
# Checklist HÍBRIDO: los campos fijos de abajo son universales (aplican a
# cualquier máquina); lo específico de cada fabricante+modelo (aceite,
# presión neumática, refrigerante, etc.) vive en ItemChecklistInspeccion
# y se responde por inspección en RespuestaChecklistInspeccion.
# ─────────────────────────────────────────────────────────────────────────────
class InspeccionDiaria(models.Model):

    maquina = models.ForeignKey(
        Maquina,
        on_delete=models.CASCADE,
        related_name='inspecciones_diarias'
    )
    inspector = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        related_name='inspecciones_realizadas'
    )

    fecha = models.DateField()

    # ── Checklist universal (aplica a cualquier máquina) ──────────────
    limpieza_area_ok = models.BooleanField(
        default=True,
        verbose_name="Área de trabajo limpia"
    )
    ruidos_anormales = models.BooleanField(
        default=False,
        verbose_name="¿Se detectaron ruidos anormales?"
    )
    vibraciones_anormales = models.BooleanField(
        default=False,
        verbose_name="¿Se detectaron vibraciones anormales?"
    )
    temperatura_normal = models.BooleanField(
        default=True,
        verbose_name="Temperatura de operación normal"
    )
    guardas_seguridad_ok = models.BooleanField(
        default=True,
        verbose_name="Guardas y protecciones de seguridad en su lugar"
    )
    boton_emergencia_ok = models.BooleanField(
        default=True,
        verbose_name="Botón de parada de emergencia operativo"
    )

    observaciones = models.TextField(blank=True)

    # Campo calculado automáticamente — ver _calcular_aprobada()
    aprobada = models.BooleanField(
        default=True,
        help_text="False si algún ítem crítico (fijo o del catálogo) falla — bloquea la máquina ese día"
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['-fecha']
        # Una inspección por máquina por día
        unique_together = [['maquina', 'fecha']]
        verbose_name = 'Inspección diaria'
        verbose_name_plural = 'Inspecciones diarias'

    def _calcular_aprobada(self):
        items_criticos_ok = self.guardas_seguridad_ok and self.boton_emergencia_ok
        items_anomalias = self.ruidos_anormales or self.vibraciones_anormales
        # Los ítems específicos del catálogo (RespuestaChecklistInspeccion) solo
        # existen una vez que la inspección ya tiene pk, por eso se evalúan aparte
        # — ver recalcular_aprobada(), llamado por la vista tras guardar las respuestas.
        dinamicos_criticos_fallidos = False
        if self.pk:
            dinamicos_criticos_fallidos = self.respuestas_checklist.filter(
                item__es_critico=True, ok=False
            ).exists()
        return items_criticos_ok and not items_anomalias and not dinamicos_criticos_fallidos

    def recalcular_aprobada(self):
        """Recalcula `aprobada` considerando las respuestas del catálogo dinámico.
        Debe llamarse después de crear/actualizar las RespuestaChecklistInspeccion."""
        self.aprobada = self._calcular_aprobada()
        self.save(update_fields=['aprobada'])

    def save(self, *args, **kwargs):
        self.aprobada = self._calcular_aprobada()
        super().save(*args, **kwargs)

    def __str__(self):
        estado = "✓" if self.aprobada else "✗ FALLIDA"
        return f"{self.maquina.codigo} — {self.fecha} [{estado}]"


# ─────────────────────────────────────────────────────────────────────────────
# Respuesta a un ítem del catálogo dinámico, para una inspección concreta.
# ─────────────────────────────────────────────────────────────────────────────
class RespuestaChecklistInspeccion(models.Model):

    inspeccion = models.ForeignKey(
        InspeccionDiaria,
        on_delete=models.CASCADE,
        related_name='respuestas_checklist'
    )
    item = models.ForeignKey(
        ItemChecklistInspeccion,
        on_delete=models.CASCADE,
        related_name='respuestas'
    )
    ok = models.BooleanField(default=True)

    class Meta:
        ordering = ['item__orden', 'item__nombre']
        unique_together = [['inspeccion', 'item']]
        verbose_name = 'Respuesta de checklist'
        verbose_name_plural = 'Respuestas de checklist'

    def __str__(self):
        return f"{self.inspeccion} — {self.item.nombre}: {'OK' if self.ok else 'FALLA'}"


# ─────────────────────────────────────────────────────────────────────────────
# Registro OEE (Pilar 3 TPM — Mejora Enfocada)
# Calculado automáticamente desde los datos de OrdenTrabajo
# ─────────────────────────────────────────────────────────────────────────────
class RegistroOEE(models.Model):

    maquina = models.ForeignKey(
        Maquina,
        on_delete=models.CASCADE,
        related_name='registros_oee'
    )

    # Período de cálculo
    mes = models.PositiveSmallIntegerField()
    anio = models.PositiveSmallIntegerField()

    # Los tres componentes del OEE (0–100)
    disponibilidad = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text="A = Tiempo real / Tiempo de carga × 100"
    )
    rendimiento = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text="P = Unidades reales / Unidades esperadas × 100"
    )
    calidad = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text="Q = Unidades sin defecto / Total unidades × 100"
    )

    # OEE calculado en save()
    oee = models.DecimalField(
        max_digits=5, decimal_places=2,
        editable=False,
        help_text="OEE = (A × P × Q) / 10000"
    )

    observaciones = models.TextField(blank=True)
    fecha_calculo = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['-anio', '-mes']
        unique_together = [['maquina', 'mes', 'anio']]
        verbose_name = 'Registro OEE'
        verbose_name_plural = 'Registros OEE'

    def save(self, *args, **kwargs):
        self.oee = (self.disponibilidad * self.rendimiento * self.calidad) / 10000
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.maquina.codigo} — {self.mes:02d}/{self.anio} OEE={self.oee}%"


# ─────────────────────────────────────────────────────────────────────────────
# Incidente / condición anormal (Pilar 7 TPM — Seguridad)
# ─────────────────────────────────────────────────────────────────────────────
class Incidente(models.Model):

    TIPOS = [
        ('CASI_ACCIDENTE', 'Casi accidente'),
        ('CONDICION_RIESGO', 'Condición de riesgo'),
        ('ACCIDENTE', 'Accidente'),
        ('ANOMALIA', 'Anomalía operacional'),
    ]

    SEVERIDADES = [
        ('BAJA', 'Baja'),
        ('MEDIA', 'Media'),
        ('ALTA', 'Alta'),
        ('CRITICA', 'Crítica'),
    ]

    maquina = models.ForeignKey(
        Maquina,
        on_delete=models.CASCADE,
        related_name='incidentes'
    )
    reportado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        related_name='incidentes_reportados'
    )

    tipo = models.CharField(max_length=20, choices=TIPOS)
    severidad = models.CharField(max_length=10, choices=SEVERIDADES)
    descripcion = models.TextField()
    accion_tomada = models.TextField(blank=True)

    requiere_mantenimiento = models.BooleanField(
        default=False,
        help_text="Si True → genera una Alerta automáticamente al ingeniero"
    )

    fecha_ocurrencia = models.DateTimeField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['-fecha_ocurrencia']
        verbose_name = 'Incidente'
        verbose_name_plural = 'Incidentes'

    def __str__(self):
        return f"{self.maquina.codigo} — {self.get_tipo_display()} ({self.fecha_ocurrencia.strftime('%d/%m/%Y')})"


# ─────────────────────────────────────────────────────────────────────────────
# Tabla ALERTA — persistencia de todas las notificaciones del sistema
#
# Sin esta tabla las alertas son solo "semáforos en pantalla" que se pierden
# si el ingeniero no entra ese día. Con ella se tiene historial completo:
# cuándo se generó, quién la vio, si fue resuelta.
#
# Se genera desde dos mecanismos:
#   1. Django signals (eventos inmediatos: inspección fallida, incidente crítico)
#   2. Management command diario vía cron (mantenimiento vencido, stock bajo, etc.)
# ─────────────────────────────────────────────────────────────────────────────
class Alerta(models.Model):

    TIPOS = [
        ('MANTENIMIENTO_PROXIMO', 'Mantenimiento próximo'),
        ('MANTENIMIENTO_VENCIDO', 'Mantenimiento vencido'),
        ('STOCK_BAJO', 'Stock de material bajo'),
        ('INSPECCION_FALLIDA', 'Inspección diaria fallida'),
        ('CERTIFICACION_POR_VENCER', 'Certificación por vencer'),
        ('CERTIFICACION_VENCIDA', 'Certificación vencida'),
        ('INCIDENTE', 'Incidente / condición de riesgo'),
        ('PARADA_NO_PLANIFICADA', 'Parada no planificada registrada'),
    ]

    SEVERIDADES = [
        ('INFO', 'Informativa'),
        ('ADVERTENCIA', 'Advertencia'),
        ('CRITICA', 'Crítica'),
    ]

    tipo = models.CharField(max_length=30, choices=TIPOS)
    severidad = models.CharField(max_length=15, choices=SEVERIDADES, default='ADVERTENCIA')

    # Contexto — ambos opcionales dependiendo del tipo de alerta
    maquina = models.ForeignKey(
        Maquina,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='alertas',
        help_text="Máquina relacionada con la alerta (si aplica)"
    )

    # Referencia genérica al objeto que originó la alerta
    referencia_id = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="ID del objeto origen (Mantenimiento, Material, Incidente, etc.)"
    )
    referencia_tipo = models.CharField(
        max_length=50, blank=True,
        help_text="Nombre del modelo origen: 'Mantenimiento', 'Material', 'Incidente'..."
    )

    mensaje = models.TextField(
        help_text="Descripción legible de la alerta para mostrar al usuario"
    )

    # Ciclo de vida
    generada_en = models.DateTimeField(auto_now_add=True)

    vista_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alertas_vistas'
    )
    vista_en = models.DateTimeField(null=True, blank=True)

    resuelta = models.BooleanField(default=False)
    resuelta_en = models.DateTimeField(null=True, blank=True)
    resuelta_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alertas_resueltas'
    )

    class Meta:
        ordering = ['-generada_en']
        verbose_name = 'Alerta'
        verbose_name_plural = 'Alertas'

    def marcar_vista(self, usuario):
        if not self.vista_en:
            self.vista_por = usuario
            self.vista_en = timezone.now()
            self.save(update_fields=['vista_por', 'vista_en'])

    def resolver(self, usuario):
        self.resuelta = True
        self.resuelta_en = timezone.now()
        self.resuelta_por = usuario
        self.save(update_fields=['resuelta', 'resuelta_en', 'resuelta_por'])

    def __str__(self):
        maquina_str = f" — {self.maquina.codigo}" if self.maquina else ""
        return f"[{self.get_severidad_display()}] {self.get_tipo_display()}{maquina_str}"


# ─────────────────────────────────────────────────────────────────────────────
# Hallazgo TPM (de inspecciones — renombrado de HallazgoTPM original)
# ─────────────────────────────────────────────────────────────────────────────
class HallazgoInspeccion(models.Model):

    PRIORIDADES = [
        ('BAJA', 'Baja'),
        ('MEDIA', 'Media'),
        ('ALTA', 'Alta'),
        ('CRITICA', 'Crítica'),
    ]

    inspeccion = models.ForeignKey(
        InspeccionDiaria,
        on_delete=models.CASCADE,
        related_name='hallazgos'
    )

    descripcion = models.TextField()
    prioridad = models.CharField(max_length=10, choices=PRIORIDADES)
    resuelto = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Hallazgo de inspección'
        verbose_name_plural = 'Hallazgos de inspección'

    def __str__(self):
        return self.descripcion[:60]