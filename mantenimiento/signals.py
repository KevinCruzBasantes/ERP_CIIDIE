"""
mantenimiento/signals.py

Genera OrdenMantenimiento automáticamente ante disparadores críticos
detectados en otras apps, sin necesidad de que un humano la confirme.

Disparadores automáticos:
  - Maquina: cambia de estado a FUERA_SERVICIO
  - InspeccionDiaria: aprobada=False
  - HallazgoInspeccion: prioridad CRITICA o ALTA
  - RegistroParada: parada no planificada (PNP) de cualquier categoría
    excepto OPERACION/OTRO (CATEGORIAS_NO_TECNICAS) — incluye SEGURIDAD

Incidente y PlanMantenimiento siguen siendo disparadores manuales
(botón "Generar orden" en su detalle), ver mantenimiento/views.py.
"""

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone

CATEGORIAS_NO_TECNICAS = ('OPERACION', 'OTRO')


@receiver(pre_save, sender='maquinas.Maquina')
def _guardar_estado_anterior(sender, instance, **kwargs):
    if instance.pk:
        from maquinas.models import Maquina
        instance._estado_anterior = (
            Maquina.objects.filter(pk=instance.pk).values_list('estado', flat=True).first()
        )
    else:
        instance._estado_anterior = None


@receiver(post_save, sender='maquinas.Maquina')
def orden_por_falla_maquina(sender, instance, created, **kwargs):
    if created:
        return
    estado_anterior = getattr(instance, '_estado_anterior', None)
    if instance.estado != 'FUERA_SERVICIO' or estado_anterior == 'FUERA_SERVICIO':
        return

    from mantenimiento.models import OrdenMantenimiento

    ya_existe = OrdenMantenimiento.objects.filter(
        maquina=instance, origen='ESTADO_MAQUINA', activo=True
    ).exclude(estado__in=['FINALIZADA', 'CANCELADA']).exists()
    if ya_existe:
        return

    OrdenMantenimiento.objects.create(
        maquina=instance,
        origen='ESTADO_MAQUINA',
        tipo='CORRECTIVO',
        prioridad='CRITICA',
        titulo=f"Correctivo: {instance.nombre} pasó a Fuera de servicio",
        descripcion_tarea=(
            "Orden generada automáticamente al marcar la máquina como "
            "Fuera de servicio. Diagnosticar y reparar antes de reanudar uso."
        ),
        fecha_programada=timezone.now().date(),
        para_produccion=True,
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
