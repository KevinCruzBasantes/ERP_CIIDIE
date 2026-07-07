from datetime import time, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from testing_comun import (
    crear_certificacion,
    crear_estudiante,
    crear_maquina,
    crear_operador,
    crear_orden_trabajo,
    crear_reserva,
    crear_tecnico,
)
from reservas.models import RegistroParada, Reserva
from usuarios.models import DisponibilidadOperador


def proximo_lunes():
    hoy = timezone.now().date()
    return hoy + timedelta(days=(0 - hoy.weekday()) % 7 or 7)


class ReservaValidacionesTest(TestCase):

    def setUp(self):
        self.tecnico = crear_tecnico()
        self.maquina = crear_maquina()

    def test_reserva_valida_se_crea(self):
        reserva = crear_reserva(self.tecnico, self.maquina)
        self.assertEqual(reserva.estado, 'PENDIENTE')

    def test_hora_fin_debe_ser_mayor_que_inicio(self):
        with self.assertRaises(ValidationError):
            crear_reserva(self.tecnico, self.maquina,
                          hora_inicio=time(11, 0), hora_fin=time(9, 0))
        with self.assertRaises(ValidationError):
            crear_reserva(self.tecnico, self.maquina,
                          hora_inicio=time(9, 0), hora_fin=time(9, 0))

    def test_maquina_no_operativa_rechaza_reserva(self):
        self.maquina.estado = 'MANTENIMIENTO'
        self.maquina.save(update_fields=['estado'])
        with self.assertRaises(ValidationError):
            crear_reserva(self.tecnico, self.maquina)

    def test_conflicto_de_horario_en_la_misma_maquina(self):
        crear_reserva(self.tecnico, self.maquina,
                      hora_inicio=time(9, 0), hora_fin=time(11, 0))
        otro = crear_tecnico()
        with self.assertRaises(ValidationError):
            crear_reserva(otro, self.maquina,
                          hora_inicio=time(10, 0), hora_fin=time(12, 0))

    def test_horarios_contiguos_no_son_conflicto(self):
        crear_reserva(self.tecnico, self.maquina,
                      hora_inicio=time(9, 0), hora_fin=time(11, 0))
        otro = crear_tecnico()
        reserva = crear_reserva(otro, self.maquina,
                                hora_inicio=time(11, 0), hora_fin=time(13, 0))
        self.assertIsNotNone(reserva.pk)

    def test_reserva_cancelada_no_bloquea_el_horario(self):
        primera = crear_reserva(self.tecnico, self.maquina)
        primera.estado = 'CANCELADA'
        primera.save()
        otro = crear_tecnico()
        reserva = crear_reserva(otro, self.maquina)  # mismo horario
        self.assertIsNotNone(reserva.pk)

    # ── Certificaciones (Pilar 4 TPM) ────────────────────────────────────

    def test_sin_certificacion_no_se_puede_reservar(self):
        with self.assertRaises(ValidationError):
            crear_reserva(self.tecnico, self.maquina, con_certificacion=False)

    def test_certificacion_vencida_no_sirve(self):
        crear_certificacion(self.tecnico, self.maquina, dias_vigencia=-1)
        with self.assertRaises(ValidationError):
            crear_reserva(self.tecnico, self.maquina, con_certificacion=False)

    def test_certificacion_inactiva_no_sirve(self):
        crear_certificacion(self.tecnico, self.maquina, activo=False)
        with self.assertRaises(ValidationError):
            crear_reserva(self.tecnico, self.maquina, con_certificacion=False)

    # ── Estudiante + operador ────────────────────────────────────────────

    def test_estudiante_sin_operador_es_rechazado(self):
        estudiante = crear_estudiante()
        crear_certificacion(estudiante, self.maquina)  # aunque esté certificado
        with self.assertRaises(ValidationError):
            crear_reserva(estudiante, self.maquina, con_certificacion=False)

    def test_estudiante_con_operador_certificado(self):
        estudiante = crear_estudiante()
        operador = crear_operador()
        crear_certificacion(operador, self.maquina)
        # el estudiante NO necesita certificación propia: la exige el operador
        reserva = crear_reserva(estudiante, self.maquina,
                                operador=operador, con_certificacion=False)
        self.assertIsNotNone(reserva.pk)

    def test_estudiante_con_operador_sin_certificar_es_rechazado(self):
        estudiante = crear_estudiante()
        operador = crear_operador()
        with self.assertRaises(ValidationError):
            crear_reserva(estudiante, self.maquina,
                          operador=operador, con_certificacion=False)

    # ── Disponibilidad horaria del operador ──────────────────────────────

    def test_operador_sin_horarios_declarados_siempre_disponible(self):
        estudiante = crear_estudiante()
        operador = crear_operador()
        reserva = crear_reserva(estudiante, self.maquina, operador=operador,
                                fecha=proximo_lunes())
        self.assertIsNotNone(reserva.pk)

    def test_operador_con_bloque_que_cubre_el_horario(self):
        estudiante = crear_estudiante()
        operador = crear_operador()
        DisponibilidadOperador.objects.create(
            operador=operador, dia_semana=0,
            hora_inicio=time(8, 0), hora_fin=time(12, 0),
        )
        reserva = crear_reserva(estudiante, self.maquina, operador=operador,
                                fecha=proximo_lunes())
        self.assertIsNotNone(reserva.pk)

    def test_operador_con_bloque_que_no_cubre_el_horario(self):
        estudiante = crear_estudiante()
        operador = crear_operador()
        DisponibilidadOperador.objects.create(
            operador=operador, dia_semana=0,
            hora_inicio=time(10, 0), hora_fin=time(12, 0),  # no cubre 9-11
        )
        with self.assertRaises(ValidationError):
            crear_reserva(estudiante, self.maquina, operador=operador,
                          fecha=proximo_lunes())

    # ── Cierre y cancelación sin revalidar (regresión 500 en cerrar_orden) ──

    def test_completar_reserva_con_certificacion_ya_vencida(self):
        """Regresión: si la certificación vence a mitad de un trabajo largo,
        cerrar la orden (estado COMPLETADA) no debe reventar con 500."""
        reserva = crear_reserva(self.tecnico, self.maquina, estado='EN_USO')
        from tpm.models import CertificacionUsuario
        CertificacionUsuario.objects.filter(usuario=self.tecnico).update(
            fecha_vencimiento=timezone.now().date() - timedelta(days=1))
        reserva.estado = 'COMPLETADA'
        reserva.save()  # no debe lanzar ValidationError
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, 'COMPLETADA')

    def test_cancelar_reserva_con_maquina_en_mantenimiento(self):
        reserva = crear_reserva(self.tecnico, self.maquina)
        self.maquina.estado = 'MANTENIMIENTO'
        self.maquina.save(update_fields=['estado'])
        reserva.estado = 'CANCELADA'
        reserva.save()  # no debe lanzar ValidationError
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, 'CANCELADA')


class RegistroParadaTest(TestCase):

    def setUp(self):
        tecnico = crear_tecnico()
        maquina = crear_maquina()
        self.ot = crear_orden_trabajo(usuario=tecnico, maquina=maquina)

    def test_duracion_calculada_automaticamente(self):
        parada = RegistroParada.objects.create(
            orden_trabajo=self.ot, hora_inicio=time(10, 0), hora_fin=time(10, 45),
            descripcion_tecnica='Prueba',
        )
        self.assertEqual(parada.duracion_minutos, 45)

    def test_duracion_cuando_cruza_medianoche(self):
        parada = RegistroParada.objects.create(
            orden_trabajo=self.ot, hora_inicio=time(23, 30), hora_fin=time(0, 15),
            descripcion_tecnica='Prueba',
        )
        self.assertEqual(parada.duracion_minutos, 45)

    def test_sin_hora_fin_no_hay_duracion(self):
        parada = RegistroParada.objects.create(
            orden_trabajo=self.ot, hora_inicio=time(10, 0),
            descripcion_tecnica='Parada aún abierta',
        )
        self.assertIsNone(parada.duracion_minutos)
