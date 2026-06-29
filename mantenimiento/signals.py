"""
mantenimiento/signals.py

Genera OrdenMantenimiento automáticamente ante disparadores críticos
detectados en otras apps, sin necesidad de que un humano la confirme.

Disparadores automáticos:
  - OrdenMantenimiento: creada o cambia a FINALIZADA/CANCELADA
    → sincroniza el estado de la máquina (OPERATIVA ↔ MANTENIMIENTO)
    El estado BAJA (dada de baja) nunca se toca automáticamente.
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
    if not maquina or maquina.estado == 'BAJA':
        return

    tiene_om_activa = sender.objects.filter(
        maquina=maquina, activo=True
    ).exclude(estado__in=['FINALIZADA', 'CANCELADA']).exists()

    if tiene_om_activa and maquina.estado == 'OPERATIVA':
        Maquina.objects.filter(pk=maquina.pk).update(estado='MANTENIMIENTO')
    elif not tiene_om_activa and maquina.estado == 'MANTENIMIENTO':
        Maquina.objects.filter(pk=maquina.pk).update(estado='OPERATIVA')


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
