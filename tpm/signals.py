"""
tpm/signals.py

Alertas generadas en tiempo real mediante Django signals.
Complementan el management command diario (generar_alertas) que
maneja alertas periódicas (mantenimiento vencido, stock bajo, etc.).

Signals activos:
  - InspeccionDiaria: si aprobada=False → ALERTA CRÍTICA
  - Incidente: si requiere_mantenimiento=True → ALERTA CRÍTICA
  - RegistroParada (PNP): → ALERTA INFORMATIVA al ingeniero
  - BitacoraOperario: si requiere_atencion=True → ALERTA ADVERTENCIA
"""

from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='tpm.InspeccionDiaria')
def alerta_inspeccion_fallida(sender, instance, created, **kwargs):
    """
    Si una inspección diaria no es aprobada → alerta crítica inmediata.
    La máquina queda efectivamente bloqueada porque Reserva.clean()
    verifica maquina.estado, y el ingeniero debe revisar antes de
    autorizar su uso.
    """
    from tpm.models import Alerta

    if not instance.aprobada:
        # Evitar duplicados para la misma máquina y fecha
        Alerta.objects.get_or_create(
            tipo='INSPECCION_FALLIDA',
            maquina=instance.maquina,
            referencia_id=instance.pk,
            referencia_tipo='InspeccionDiaria',
            resuelta=False,
            defaults={
                'severidad': 'CRITICA',
                'mensaje': (
                    f"Inspección diaria FALLIDA en {instance.maquina.nombre} "
                    f"el {instance.fecha.strftime('%d/%m/%Y')}. "
                    f"Revisar antes de autorizar uso de la máquina."
                ),
            }
        )


@receiver(post_save, sender='tpm.Incidente')
def alerta_incidente_mantenimiento(sender, instance, created, **kwargs):
    """
    Si un incidente requiere mantenimiento → alerta crítica al ingeniero.
    """
    from tpm.models import Alerta

    if instance.requiere_mantenimiento and created:
        Alerta.objects.create(
            tipo='INCIDENTE',
            severidad='CRITICA',
            maquina=instance.maquina,
            referencia_id=instance.pk,
            referencia_tipo='Incidente',
            mensaje=(
                f"Incidente en {instance.maquina.nombre} requiere mantenimiento: "
                f"{instance.get_tipo_display()} — {instance.descripcion[:100]}"
            ),
        )


@receiver(post_save, sender='reservas.RegistroParada')
def alerta_parada_no_planificada(sender, instance, created, **kwargs):
    """
    Cuando se registra una parada no planificada (PNP) → alerta informativa.
    Contribuye al análisis Pareto del dashboard.
    """
    from tpm.models import Alerta

    if not created:
        return

    es_pnp = (
        instance.codigo_parada
        and instance.codigo_parada.tipo == 'NO_PLANIFICADA'
    )
    if es_pnp:
        maquina = instance.orden_trabajo.reserva.maquina
        Alerta.objects.create(
            tipo='PARADA_NO_PLANIFICADA',
            severidad='ADVERTENCIA',
            maquina=maquina,
            referencia_id=instance.pk,
            referencia_tipo='RegistroParada',
            mensaje=(
                f"Parada no planificada [{instance.codigo_parada.codigo}] "
                f"en {maquina.nombre}: {instance.codigo_parada.subsistema}. "
                f"Duración: {instance.duracion_minutos or '?'} min."
            ),
        )


@receiver(post_save, sender='reservas.BitacoraOperario')
def alerta_bitacora_atencion(sender, instance, created, **kwargs):
    """
    Cuando un operario marca "requiere atención" en la bitácora de una
    orden de trabajo → alerta de advertencia, visible en el dashboard del
    técnico, con link de vuelta a la orden de trabajo de origen.
    """
    from tpm.models import Alerta

    if not created or not instance.requiere_atencion:
        return

    maquina = instance.orden_trabajo.reserva.maquina
    operario_str = instance.operario.get_full_name() if instance.operario else 'operario eliminado'

    # No hace falta get_or_create: created=True solo es verdadero una vez
    # por entrada de bitacora nueva, no hay riesgo de alerta duplicada.
    Alerta.objects.create(
        tipo='BITACORA_ATENCION',
        severidad='ADVERTENCIA',
        maquina=maquina,
        referencia_id=instance.orden_trabajo_id,
        referencia_tipo='OrdenTrabajo',
        mensaje=(
            f"{operario_str} marcó la bitácora de OT-{instance.orden_trabajo_id:04d} "
            f"({maquina.nombre}) como que requiere atención: "
            f"{instance.descripcion_trabajo[:100]}"
        ),
    )