from datetime import time, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from testing_comun import (
    crear_codigo_parada,
    crear_maquina,
    crear_orden_trabajo,
    crear_reserva,
    crear_tecnico,
)
from mantenimiento.models import Mantenimiento, OrdenMantenimiento
from tpm.models import Alerta


def crear_om(maquina, **extra):
    datos = dict(maquina=maquina, titulo='OM de prueba',
                 fecha_programada=timezone.now().date())
    datos.update(extra)
    return OrdenMantenimiento.objects.create(**datos)


class MantenimientoModelTest(TestCase):

    def setUp(self):
        self.maquina = crear_maquina()

    def crear_mantenimiento(self, **extra):
        datos = dict(maquina=self.maquina, tipo='PREVENTIVO',
                     descripcion='Lubricación general',
                     fecha_programada=timezone.now().date())
        datos.update(extra)
        return Mantenimiento(**datos)

    def test_fecha_fin_menor_que_inicio_es_invalida(self):
        ahora = timezone.now()
        mantenimiento = self.crear_mantenimiento(
            fecha_inicio=ahora, fecha_fin=ahora - timedelta(hours=2))
        with self.assertRaises(ValidationError):
            mantenimiento.full_clean()

    def test_esta_vencido(self):
        ayer = timezone.now().date() - timedelta(days=1)
        vencido = self.crear_mantenimiento(fecha_programada=ayer)
        self.assertTrue(vencido.esta_vencido)
        futuro = self.crear_mantenimiento(
            fecha_programada=timezone.now().date() + timedelta(days=3))
        self.assertFalse(futuro.esta_vencido)
        finalizado = self.crear_mantenimiento(fecha_programada=ayer,
                                              estado='FINALIZADO')
        self.assertFalse(finalizado.esta_vencido)

    def test_dias_para_vencer(self):
        mantenimiento = self.crear_mantenimiento(
            fecha_programada=timezone.now().date() + timedelta(days=7))
        self.assertEqual(mantenimiento.dias_para_vencer, 7)


class SincronizacionEstadoMaquinaTest(TestCase):
    """Signal sincronizar_estado_maquina: OM activa ↔ estado de la máquina."""

    def setUp(self):
        self.maquina = crear_maquina()

    def test_om_nueva_pone_la_maquina_en_mantenimiento(self):
        crear_om(self.maquina)
        self.maquina.refresh_from_db()
        self.assertEqual(self.maquina.estado, 'MANTENIMIENTO')

    def test_finalizar_la_om_devuelve_la_maquina_a_operativa(self):
        om = crear_om(self.maquina)
        om.estado = 'FINALIZADA'
        om.save()
        self.maquina.refresh_from_db()
        self.assertEqual(self.maquina.estado, 'OPERATIVA')

    def test_con_dos_om_abiertas_hay_que_cerrar_ambas(self):
        om1 = crear_om(self.maquina)
        om2 = crear_om(self.maquina, titulo='Segunda OM')
        om1.estado = 'FINALIZADA'
        om1.save()
        self.maquina.refresh_from_db()
        self.assertEqual(self.maquina.estado, 'MANTENIMIENTO')
        om2.estado = 'CANCELADA'
        om2.save()
        self.maquina.refresh_from_db()
        self.assertEqual(self.maquina.estado, 'OPERATIVA')

    def test_maquina_dada_de_baja_nunca_se_toca(self):
        self.maquina.estado = 'BAJA'
        self.maquina.save(update_fields=['estado'])
        crear_om(self.maquina)
        self.maquina.refresh_from_db()
        self.assertEqual(self.maquina.estado, 'BAJA')

    def test_reserva_aprobada_recibe_alerta_y_se_resuelve_al_finalizar(self):
        tecnico = crear_tecnico()
        crear_reserva(tecnico, self.maquina, estado='APROBADA')

        om = crear_om(self.maquina)
        alertas = Alerta.objects.filter(tipo='RESERVA_AFECTADA_MANTENIMIENTO')
        self.assertEqual(alertas.count(), 1)
        self.assertFalse(alertas.first().resuelta)

        om.estado = 'FINALIZADA'
        om.save()
        alerta = alertas.first()
        alerta.refresh_from_db()
        self.assertTrue(alerta.resuelta)
        self.assertIn('volvió a estado operativo', alerta.nota_resolucion)

    def test_reserva_pendiente_no_genera_alerta(self):
        tecnico = crear_tecnico()
        crear_reserva(tecnico, self.maquina, estado='PENDIENTE')
        crear_om(self.maquina)
        self.assertEqual(
            Alerta.objects.filter(tipo='RESERVA_AFECTADA_MANTENIMIENTO').count(), 0)


class OrdenesAutomaticasTest(TestCase):
    """Signals que crean OrdenMantenimiento desde otros módulos."""

    def setUp(self):
        self.maquina = crear_maquina()
        self.tecnico = crear_tecnico()

    def test_numero_de_orden(self):
        om = crear_om(self.maquina)
        self.assertEqual(om.numero(), f'OM-{om.pk:04d}')

    def test_inspeccion_fallida_crea_om_sin_duplicar(self):
        from tpm.models import InspeccionDiaria
        inspeccion = InspeccionDiaria.objects.create(
            maquina=self.maquina, inspector=self.tecnico,
            fecha=timezone.now().date(), boton_emergencia_ok=False)
        oms = OrdenMantenimiento.objects.filter(origen='INSPECCION',
                                                inspeccion=inspeccion)
        self.assertEqual(oms.count(), 1)
        self.assertEqual(oms.first().prioridad, 'ALTA')
        inspeccion.save()  # re-guardar no debe duplicar
        self.assertEqual(oms.count(), 1)

    def test_inspeccion_aprobada_no_crea_om(self):
        from tpm.models import InspeccionDiaria
        InspeccionDiaria.objects.create(
            maquina=self.maquina, inspector=self.tecnico,
            fecha=timezone.now().date())
        self.assertEqual(
            OrdenMantenimiento.objects.filter(origen='INSPECCION').count(), 0)

    def test_hallazgo_critico_crea_om_con_su_prioridad(self):
        from tpm.models import HallazgoInspeccion, InspeccionDiaria
        inspeccion = InspeccionDiaria.objects.create(
            maquina=self.maquina, inspector=self.tecnico,
            fecha=timezone.now().date())
        hallazgo = HallazgoInspeccion.objects.create(
            inspeccion=inspeccion, descripcion='Cable pelado', prioridad='CRITICA')
        oms = OrdenMantenimiento.objects.filter(origen='HALLAZGO', hallazgo=hallazgo)
        self.assertEqual(oms.count(), 1)
        self.assertEqual(oms.first().prioridad, 'CRITICA')

    def test_hallazgo_menor_no_crea_om(self):
        from tpm.models import HallazgoInspeccion, InspeccionDiaria
        inspeccion = InspeccionDiaria.objects.create(
            maquina=self.maquina, inspector=self.tecnico,
            fecha=timezone.now().date())
        HallazgoInspeccion.objects.create(
            inspeccion=inspeccion, descripcion='Pintura rayada', prioridad='BAJA')
        self.assertEqual(
            OrdenMantenimiento.objects.filter(origen='HALLAZGO').count(), 0)

    def _crear_parada(self, codigo):
        from reservas.models import RegistroParada
        ot = crear_orden_trabajo(usuario=self.tecnico, maquina=self.maquina)
        return RegistroParada.objects.create(
            orden_trabajo=ot, codigo_parada=codigo,
            hora_inicio=time(10, 0), hora_fin=time(10, 30),
            descripcion_tecnica='Parada de prueba')

    def test_parada_tecnica_no_planificada_crea_om(self):
        parada = self._crear_parada(
            crear_codigo_parada(tipo='NO_PLANIFICADA', categoria='MECANICA'))
        self.assertEqual(
            OrdenMantenimiento.objects.filter(origen='PARADA', parada=parada).count(), 1)

    def test_parada_de_operacion_no_crea_om(self):
        self._crear_parada(
            crear_codigo_parada(tipo='NO_PLANIFICADA', categoria='OPERACION'))
        self.assertEqual(
            OrdenMantenimiento.objects.filter(origen='PARADA').count(), 0)

    def test_parada_planificada_no_crea_om(self):
        self._crear_parada(
            crear_codigo_parada(tipo='PLANIFICADA', categoria='MECANICA'))
        self.assertEqual(
            OrdenMantenimiento.objects.filter(origen='PARADA').count(), 0)

    def test_bitacora_que_requiere_atencion_crea_om(self):
        from reservas.models import BitacoraOperario
        ot = crear_orden_trabajo(usuario=self.tecnico, maquina=self.maquina)
        bitacora = BitacoraOperario.objects.create(
            orden_trabajo=ot, operario=self.tecnico,
            descripcion_trabajo='Ruido extraño en el husillo',
            requiere_atencion=True)
        oms = OrdenMantenimiento.objects.filter(origen='BITACORA',
                                                bitacora_operario=bitacora)
        self.assertEqual(oms.count(), 1)
        self.assertEqual(oms.first().prioridad, 'MEDIA')

    def test_bitacora_normal_no_crea_om(self):
        from reservas.models import BitacoraOperario
        ot = crear_orden_trabajo(usuario=self.tecnico, maquina=self.maquina)
        BitacoraOperario.objects.create(
            orden_trabajo=ot, operario=self.tecnico,
            descripcion_trabajo='Sin novedades')
        self.assertEqual(
            OrdenMantenimiento.objects.filter(origen='BITACORA').count(), 0)
