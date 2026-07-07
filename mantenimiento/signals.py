"""
mantenimiento/signals.py

Genera OrdenMantenimiento automáticamente ante disparadores críticos
detectados en otras apps, sin necesidad de que un humano la confirme.

Disparadores automáticos:
  - OrdenMantenimiento: creada o cambia a FINALIZADA/CANCELADA
    → sincroniza el estado de la máquina (OPERATIVA ↔ MANTENIMIENTO)
    El estado BAJA (dada de baja) nunca se toca automáticamente.
    → al entrar en MANTENIMIENTO, genera una Alerta por cada Reserva ya
      APROBADA/EN_USO de esa máquina (hoy o a futuro); al volver a OPERATIVA,
      esas alertas se resuelven automáticamente.
  - InspeccionDiaria: aprobada=False
  - HallazgoInspeccion: prioridad CRITICA o ALTA
  - RegistroParada: parada no planificada (PNP) de cualquier categoría
    excepto OPERACION/OTRO (CATEGORIAS_NO_TECNICAS) — incluye SEGURIDAD
  - BitacoraOperario: requiere_atencion=True

Incidente y PlanMantenimiento siguen siendo disparadores manuales
(botón "Generar orden" en su detalle), ver mantenimiento/views.py.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

CATEGORIAS_NO_TECNICAS = ('OPERACION', 'OTRO')


@receiver(post_save, sender='mantenimiento.OrdenMantenimiento')
def sincronizar_estado_maquina(sender, instance, **kwargs):
    """Mantiene el estado de la máquina sincronizado con sus OMs activas."""
    from maquinas.models import Maquina
    maquina = instance.maquina
    if not maquina:
        return
    # El estado se consulta en BD: instance.maquina puede venir cacheado en
    # memoria con un estado viejo (p.ej. al crear y finalizar la OM con el
    # mismo objeto) y dejaría la máquina atascada en MANTENIMIENTO.
    estado_actual = (Maquina.objects.filter(pk=maquina.pk)
                     .values_list('estado', flat=True).first())
    if estado_actual is None or estado_actual == 'BAJA':
        return

    tiene_om_activa = sender.objects.filter(
        maquina=maquina, activo=True
    ).exclude(estado__in=['FINALIZADA', 'CANCELADA']).exists()

    if tiene_om_activa and estado_actual == 'OPERATIVA':
        Maquina.objects.filter(pk=maquina.pk).update(estado='MANTENIMIENTO')
        _alertar_reservas_por_mantenimiento(maquina)
    elif not tiene_om_activa and estado_actual == 'MANTENIMIENTO':
        Maquina.objects.filter(pk=maquina.pk).update(estado='OPERATIVA')
        _resolver_alertas_reservas_por_mantenimiento(maquina)


def _alertar_reservas_por_mantenimiento(maquina):
    """Genera una Alerta por cada reserva ya aprobada/en uso (hoy o a futuro)
    de una máquina que acaba de entrar en MANTENIMIENTO."""
    from reservas.models import Reserva
    from tpm.models import Alerta

    reservas_afectadas = Reserva.objects.filter(
        maquina=maquina,
        estado__in=('APROBADA', 'EN_USO'),
        fecha__gte=timezone.now().date(),
    ).select_related('usuario')

    for reserva in reservas_afectadas:
        nombre = (
            reserva.usuario.get_full_name() or reserva.usuario.username
            if reserva.usuario else 'usuario eliminado'
        )
        Alerta.objects.get_or_create(
            tipo='RESERVA_AFECTADA_MANTENIMIENTO',
            maquina=maquina,
            referencia_id=reserva.pk,
            referencia_tipo='Reserva',
            resuelta=False,
            defaults={
                'severidad': 'ADVERTENCIA',
                'mensaje': (
                    f"{maquina.nombre} entró en mantenimiento y tiene una reserva "
                    f"{reserva.get_estado_display().lower()} de {nombre} el "
                    f"{reserva.fecha.strftime('%d/%m/%Y')} de {reserva.hora_inicio.strftime('%H:%M')} "
                    f"a {reserva.hora_fin.strftime('%H:%M')} que podría no poder cumplirse."
                ),
            }
        )


def _resolver_alertas_reservas_por_mantenimiento(maquina):
    """Al volver la máquina a OPERATIVA, resuelve las alertas de reserva que ya no aplican."""
    from tpm.models import Alerta

    Alerta.objects.filter(
        tipo='RESERVA_AFECTADA_MANTENIMIENTO',
        maquina=maquina,
        resuelta=False,
    ).update(
        resuelta=True,
        resuelta_en=timezone.now(),
        nota_resolucion='Resuelta automáticamente: la máquina volvió a estado operativo.',
    )


@receiver(post_save, sender='tpm.InspeccionDiaria')
def orden_por_inspeccion_fallida(sender, instance, created, **kwargs):
    if instance.aprobada:
        return

    from mantenimiento.models import OrdenMantenimiento

    OrdenMantenimiento.objects.get_or_create(
        maquina=instance.maquina,
        origen='INSPECCION',
        inspeccion=instance,
        defaults={
            'tipo': 'CORRECTIVO',
            'prioridad': 'ALTA',
            'titulo': f"Correctivo: inspección diaria reprobada — {instance.maquina.nombre}",
            'descripcion_tarea': (
                f"Inspección diaria del {instance.fecha.strftime('%d/%m/%Y')} no aprobada. "
                "Revisar checklist antes de autorizar el uso de la máquina."
            ),
            'fecha_programada': timezone.now().date(),
        }
    )


@receiver(post_save, sender='tpm.HallazgoInspeccion')
def orden_por_hallazgo_critico(sender, instance, created, **kwargs):
    if not created or instance.prioridad not in ('CRITICA', 'ALTA'):
        return

    from mantenimiento.models import OrdenMantenimiento

    OrdenMantenimiento.objects.get_or_create(
        maquina=instance.inspeccion.maquina,
        origen='HALLAZGO',
        hallazgo=instance,
        defaults={
            'tipo': 'CORRECTIVO',
            'prioridad': instance.prioridad,
            'titulo': (
                f"Correctivo: hallazgo {instance.get_prioridad_display().lower()} "
                f"— {instance.inspeccion.maquina.nombre}"
            ),
            'descripcion_tarea': instance.descripcion,
            'fecha_programada': timezone.now().date(),
        }
    )


@receiver(post_save, sender='reservas.RegistroParada')
def orden_por_parada_tecnica(sender, instance, created, **kwargs):
    if not created:
        return

    codigo = instance.codigo_parada
    if not codigo or codigo.tipo != 'NO_PLANIFICADA' or codigo.categoria in CATEGORIAS_NO_TECNICAS:
        return

    from mantenimiento.models import OrdenMantenimiento

    maquina = instance.orden_trabajo.reserva.maquina

    OrdenMantenimiento.objects.get_or_create(
        maquina=maquina,
        origen='PARADA',
        parada=instance,
        defaults={
            'tipo': 'CORRECTIVO',
            'prioridad': 'ALTA',
            'titulo': f"Correctivo: parada no planificada [{codigo.codigo}] — {maquina.nombre}",
            'descripcion_tarea': (
                f"{codigo.get_categoria_display()} — {codigo.subsistema}. "
                f"Duración registrada: {instance.duracion_minutos or '?'} min."
            ),
            'fecha_programada': timezone.now().date(),
        }
    )


@receiver(post_save, sender='reservas.BitacoraOperario')
def orden_por_bitacora_atencion(sender, instance, created, **kwargs):
    if not created or not instance.requiere_atencion:
        return

    from mantenimiento.models import OrdenMantenimiento

    maquina = instance.orden_trabajo.reserva.maquina
    operario_str = instance.operario.get_full_name() if instance.operario else 'operario eliminado'

    OrdenMantenimiento.objects.get_or_create(
        maquina=maquina,
        origen='BITACORA',
        bitacora_operario=instance,
        defaults={
            'tipo': 'CORRECTIVO',
            'prioridad': 'MEDIA',
            'titulo': f"Correctivo: bitácora requiere atención — {maquina.nombre}",
            'descripcion_tarea': (
                f"Reportado por {operario_str} en la bitácora de OT-{instance.orden_trabajo_id:04d}: "
                f"{instance.descripcion_trabajo}"
                + (f" Observaciones: {instance.observaciones}" if instance.observaciones else '')
            ),
            'fecha_programada': timezone.now().date(),
        }
    )
