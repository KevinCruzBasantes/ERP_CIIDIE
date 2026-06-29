from django.db import models
from django.core.validators import MinValueValidator

from usuarios.models import Usuario


class Maquina(models.Model):

    ESTADOS = [
        ('OPERATIVA', 'Operativa'),
        ('MANTENIMIENTO', 'Mantenimiento'),
        ('BAJA', 'Dada de baja'),
    ]

    # ── Identificación ────────────────────────────────────────────────
    nombre = models.CharField(max_length=150)
    codigo = models.CharField(max_length=50, unique=True)
    numero_serie = models.CharField(max_length=100, blank=True)
    codigo_barras_universidad = models.CharField(max_length=100, blank=True)

    # ── Fabricante / modelo ───────────────────────────────────────────
    fabricante = models.CharField(max_length=100, blank=True)
    modelo = models.CharField(max_length=100, blank=True)
    anio_fabricacion = models.PositiveSmallIntegerField(null=True, blank=True)

    # ── Ubicación y descripción ───────────────────────────────────────
    ubicacion = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)

    # ── Estado ────────────────────────────────────────────────────────
    estado = models.CharField(
        max_length=30,
        choices=ESTADOS,
        default='OPERATIVA'
    )

    responsable = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='maquinas_a_cargo'
    )

    # ── Archivos ──────────────────────────────────────────────────────
    imagen = models.ImageField(upload_to='maquinas/', blank=True, null=True)
    manual_pdf = models.FileField(upload_to='manuales/', blank=True, null=True)

    # ── Ficha técnica (datos del fabricante para validar inspecciones) ─
    voltaje_v = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Tensión de alimentación en voltios (ej. 400)"
    )
    frecuencia_hz = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Frecuencia de red en Hz (ej. 50)"
    )
    presion_neumatica_min_bar = models.DecimalField(
        max_digits=4, decimal_places=1,
        null=True, blank=True,
        help_text="Presión neumática mínima de operación en bar"
    )
    presion_neumatica_max_bar = models.DecimalField(
        max_digits=4, decimal_places=1,
        null=True, blank=True,
        help_text="Presión neumática máxima de operación en bar"
    )
    capacidad_refrigerante_l = models.DecimalField(
        max_digits=7, decimal_places=2,
        null=True, blank=True,
        help_text="Capacidad del tanque de refrigerante en litros"
    )
    rpm_husillo_max = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="RPM máximo del husillo principal"
    )
    tipo_control_cnc = models.CharField(
        max_length=100, blank=True,
        help_text="Tipo de controlador CNC, si aplica"
    )
    peso_kg = models.DecimalField(
        max_digits=8, decimal_places=2,
        null=True, blank=True
    )
    largo_mm = models.PositiveIntegerField(null=True, blank=True)
    ancho_mm = models.PositiveIntegerField(null=True, blank=True)
    alto_mm = models.PositiveIntegerField(null=True, blank=True)

    fecha_adquisicion = models.DateField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    horas_acumuladas = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Horas de operación acumuladas desde registros de OT cerradas"
    )

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Máquina'
        verbose_name_plural = 'Máquinas'

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    @property
    def disponible_para_reserva(self):
        return self.estado == 'OPERATIVA'


# ─────────────────────────────────────────────────────────────────────────────
# Catálogo de códigos de parada — vinculado a fabricante+modelo (NO a instancia)
# Permite que cada tipo de máquina tenga su propio diccionario de paradas,
# reutilizable si el laboratorio tiene varias unidades del mismo modelo.
# ─────────────────────────────────────────────────────────────────────────────
class CodigoParada(models.Model):

    TIPOS = [
        ('PLANIFICADA', 'Planificada (PP)'),
        ('NO_PLANIFICADA', 'No planificada (PNP)'),
    ]

    CATEGORIAS = [
        ('MECANICA', 'Mecánica'),
        ('ELECTRICA', 'Eléctrica'),
        ('NEUMATICA', 'Neumática'),
        ('LUBRICACION', 'Lubricación'),
        ('REFRIGERACION', 'Refrigeración'),
        ('CONTROL_CNC', 'Control CNC / Programación'),
        ('SEGURIDAD', 'Seguridad'),
        ('OPERACION', 'Operación / Setup'),
        ('OTRO', 'Otro'),
    ]

    # Scope: fabricante + modelo (no instancia específica)
    # Una fresadora OPTIMUM F210HSC tiene sus propios códigos;
    # un router 1313 tendrá los suyos sin mezclarlos.
    fabricante = models.CharField(
        max_length=100,
        help_text="Nombre del fabricante de la máquina"
    )
    modelo_maquina = models.CharField(
        max_length=100,
        help_text="Modelo de la máquina — el código aplica a todas las máquinas de este fabricante+modelo"
    )

    codigo = models.CharField(
        max_length=20,
        help_text="Ej: PP01, PNP-M01"
    )
    tipo = models.CharField(max_length=20, choices=TIPOS)
    categoria = models.CharField(max_length=30, choices=CATEGORIAS)
    subsistema = models.CharField(
        max_length=200,
        help_text="Subsistema o componente afectado, ej: Motor principal, Sistema de transmisión"
    )
    causa_raiz_comun = models.TextField(
        blank=True,
        help_text="Descripción técnica de la causa raíz más frecuente"
    )

    class Meta:
        ordering = ['fabricante', 'modelo_maquina', 'tipo', 'codigo']
        # Un código es único por modelo de máquina
        unique_together = [['fabricante', 'modelo_maquina', 'codigo']]
        verbose_name = 'Código de parada'
        verbose_name_plural = 'Códigos de parada'

    def __str__(self):
        return f"[{self.modelo_maquina}] {self.codigo} — {self.subsistema}"


# ─────────────────────────────────────────────────────────────────────────────
# Pieza con jerarquía auto-referenciada (Baugruppe → Pieza individual)
#
# Estructura del manual de despiece (ej. F210HSC cap. 12):
#   Nivel 0 → Máquina (MAQUINA)
#   Nivel 1 → Ensamble / Baugruppe  (PIEZA donde es_ensamble=True, ensamble=NULL)
#             Ej: "Eje X", "Cabezal de fresado", "Cambiador herramientas"
#   Nivel 2 → Pieza individual      (PIEZA donde es_ensamble=False, ensamble=<nivel1>)
#             Ej: Motor 1FK7063, Husillo de bolas, Lagerdeckel
# ─────────────────────────────────────────────────────────────────────────────
class Pieza(models.Model):

    maquina = models.ForeignKey(
        Maquina,
        on_delete=models.CASCADE,
        related_name='piezas'
    )

    # FK auto-referenciado: NULL = es un ensamble raíz
    ensamble = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='piezas_hijas',
        help_text="Ensamble padre. Dejar vacío si esta pieza ES el ensamble."
    )

    es_ensamble = models.BooleanField(
        default=False,
        help_text="Marcar si esta entrada representa un subconjunto (ensamble), no una pieza individual"
    )

    # ── Identificación ────────────────────────────────────────────────
    nombre = models.CharField(
        max_length=150,
        help_text="Nombre en español / nombre operativo"
    )
    nombre_original = models.CharField(
        max_length=150,
        blank=True,
        help_text="Nombre en el idioma del manual del fabricante, si es distinto del español"
    )
    nombre_en = models.CharField(
        max_length=150,
        blank=True,
        help_text="Nombre en inglés según el manual del fabricante"
    )
    numero_parte = models.CharField(
        max_length=50,
        blank=True,
        help_text="Código o número de parte del fabricante — necesario para pedir repuestos"
    )
    numero_posicion = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Número de posición en el diagrama del manual (Pos.)"
    )

    # ── Datos técnicos ────────────────────────────────────────────────
    especificacion = models.CharField(
        max_length=200,
        blank=True,
        help_text="Talla o especificación técnica (ej: M8xP1.25x20L, 30TAC62BSUC10PN7B)"
    )
    cantidad_en_maquina = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=1,
        validators=[MinValueValidator(0)],
        help_text="Cantidad de esta pieza instalada en la máquina (Qty del manual)"
    )

    # ── Descripción y ubicación ───────────────────────────────────────
    descripcion = models.TextField(blank=True)
    ubicacion_en_maquina = models.CharField(
        max_length=200,
        blank=True,
        help_text="Descripción textual de dónde está físicamente en la máquina"
    )
    imagen_ubicacion = models.ImageField(
        upload_to='piezas/ubicacion/',
        blank=True,
        null=True,
        help_text="Imagen de referencia mostrando la ubicación en la máquina"
    )
    imagen_pieza = models.ImageField(
        upload_to='piezas/fotos/',
        blank=True,
        null=True
    )

    # ── Inventario de repuestos ───────────────────────────────────────
    stock_repuestos = models.PositiveIntegerField(
        default=0,
        help_text="Unidades de repuesto disponibles en bodega"
    )
    stock_minimo_repuestos = models.PositiveIntegerField(
        default=0,
        help_text="Alerta cuando el stock baje de este valor"
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True, null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['maquina', 'numero_posicion', 'nombre']
        verbose_name = 'Pieza'
        verbose_name_plural = 'Piezas'

    def __str__(self):
        if self.es_ensamble:
            return f"[Ensamble] {self.nombre} ({self.maquina.codigo})"
        prefijo = f"{self.ensamble.nombre} › " if self.ensamble else ""
        return f"{prefijo}{self.nombre}"

    @property
    def stock_bajo(self):
        return (
            not self.es_ensamble
            and self.stock_repuestos <= self.stock_minimo_repuestos
        )

    def get_ruta_completa(self):
        """Devuelve la ruta jerárquica: Máquina > Ensamble > Pieza"""
        partes = [self.maquina.nombre]
        if self.ensamble:
            partes.append(self.ensamble.nombre)
        partes.append(self.nombre)
        return ' › '.join(partes)


# ─────────────────────────────────────────────────────────────────────────────
# Transferencia de piezas entre máquinas
# FKs reales a Maquina en lugar de CharField (corrige diseño original)
# ─────────────────────────────────────────────────────────────────────────────
class TransferenciaPieza(models.Model):

    pieza = models.ForeignKey(
        Pieza,
        on_delete=models.CASCADE,
        related_name='transferencias'
    )
    maquina_origen = models.ForeignKey(
        Maquina,
        on_delete=models.CASCADE,
        related_name='transferencias_origen',
        null=True,
        blank=True,
        help_text="Máquina de la que se retira la pieza"
    )
    maquina_destino = models.ForeignKey(
        Maquina,
        on_delete=models.CASCADE,
        related_name='transferencias_destino',
        null=True,
        blank=True,
        help_text="Máquina a la que se instala la pieza"
    )
    autorizado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transferencias_autorizadas'
    )

    fecha = models.DateTimeField(auto_now_add=True)
    motivo = models.TextField(help_text="Razón de la transferencia",blank=True,default='')
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Transferencia de pieza'
        verbose_name_plural = 'Transferencias de piezas'

    def __str__(self):
        return (
            f"{self.pieza.nombre}: "
            f"{self.maquina_origen.codigo} → {self.maquina_destino.codigo} "
            f"({self.fecha.strftime('%d/%m/%Y')})"
        )


class ReasignacionPieza(models.Model):

    pieza = models.ForeignKey(
        Pieza,
        on_delete=models.CASCADE,
        related_name='reasignaciones'
    )
    ensamble_anterior = models.ForeignKey(
        Pieza,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reasignaciones_salida',
        help_text="Ensamble del que salió la pieza (None = era pieza suelta)"
    )
    ensamble_nuevo = models.ForeignKey(
        Pieza,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reasignaciones_entrada',
        help_text="Ensamble al que se asignó (None = quedó suelta)"
    )
    realizado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reasignaciones_realizadas'
    )
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Reasignación de pieza'
        verbose_name_plural = 'Reasignaciones de piezas'

    def __str__(self):
        ant = self.ensamble_anterior.nombre if self.ensamble_anterior else 'suelta'
        nvo = self.ensamble_nuevo.nombre if self.ensamble_nuevo else 'suelta'
        return f"{self.pieza.nombre}: {ant} → {nvo} ({self.fecha.strftime('%d/%m/%Y')})"