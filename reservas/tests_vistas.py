from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from testing_comun import (
    crear_certificacion,
    crear_estudiante,
    crear_maquina,
    crear_orden_trabajo,
    crear_reserva,
    crear_tecnico,
    crear_usuario,
)
from reservas.models import OrdenTrabajo, Reserva


class FlujoReservaTest(TestCase):

    def setUp(self):
        self.tecnico = crear_tecnico()
        self.maquina = crear_maquina()
        self.client.force_login(self.tecnico)

    def test_crear_reserva_por_formulario(self):
        crear_certificacion(self.tecnico, self.maquina)
        manana = timezone.now().date() + timedelta(days=1)
        respuesta = self.client.post(reverse('crear_reserva'), {
            'maquina':     self.maquina.pk,
            'fecha':       manana.isoformat(),
            'hora_inicio': '09:00',
            'hora_fin':    '11:00',
            'proposito':   'PRODUCCION',
        })
        reserva = Reserva.objects.get()
        self.assertRedirects(respuesta, reverse('detalle_reserva', args=[reserva.pk]))
        self.assertEqual(reserva.estado, 'PENDIENTE')
        self.assertEqual(reserva.usuario, self.tecnico)

    def test_no_puede_aprobar_su_propia_reserva(self):
        reserva = crear_reserva(self.tecnico, self.maquina)
        self.client.post(reverse('cambiar_estado_reserva', args=[reserva.pk]),
                         {'estado': 'APROBADA'})
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, 'PENDIENTE')

    def test_otro_tecnico_aprueba_y_queda_como_autorizador(self):
        reserva = crear_reserva(self.tecnico, self.maquina)
        aprobador = crear_tecnico()
        self.client.force_login(aprobador)
        self.client.post(reverse('cambiar_estado_reserva', args=[reserva.pk]),
                         {'estado': 'APROBADA'})
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, 'APROBADA')
        self.assertEqual(reserva.autorizador, aprobador)

    def test_estudiante_no_puede_cambiar_estados(self):
        reserva = crear_reserva(self.tecnico, self.maquina)
        self.client.force_login(crear_estudiante())
        self.client.post(reverse('cambiar_estado_reserva', args=[reserva.pk]),
                         {'estado': 'APROBADA'})
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, 'PENDIENTE')

    def test_estudiante_no_ve_reservas_ajenas(self):
        reserva = crear_reserva(self.tecnico, self.maquina)
        self.client.force_login(crear_estudiante())
        respuesta = self.client.get(reverse('detalle_reserva', args=[reserva.pk]))
        self.assertEqual(respuesta.status_code, 302)

    def test_lista_de_estudiante_solo_muestra_las_suyas(self):
        crear_reserva(self.tecnico, self.maquina)
        estudiante = crear_estudiante()
        operador = crear_usuario(rol='OPERADOR')
        crear_certificacion(operador, self.maquina)
        propia = crear_reserva(estudiante, self.maquina, operador=operador,
                               fecha=timezone.now().date() + timedelta(days=2))
        self.client.force_login(estudiante)
        respuesta = self.client.get(reverse('lista_reservas'))
        self.assertEqual(respuesta.context['total'], 1)
        self.assertEqual(respuesta.context['reservas'][0].pk, propia.pk)


class FlujoOrdenTrabajoTest(TestCase):

    def setUp(self):
        self.tecnico = crear_tecnico()
        self.maquina = crear_maquina()
        self.client.force_login(self.tecnico)

    def test_crear_orden_desde_reserva_aprobada(self):
        reserva = crear_reserva(self.tecnico, self.maquina, estado='APROBADA')
        respuesta = self.client.post(reverse('crear_orden', args=[reserva.pk]), {
            'descripcion': 'Fresado de probetas',
            'tiempo_planificado_min': 120,
        })
        orden = OrdenTrabajo.objects.get()
        self.assertRedirects(respuesta, reverse('detalle_orden', args=[orden.pk]))
        self.assertEqual(orden.estado, 'ABIERTA')
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, 'EN_USO')

    def test_reserva_pendiente_no_permite_crear_orden(self):
        reserva = crear_reserva(self.tecnico, self.maquina)  # PENDIENTE
        respuesta = self.client.post(reverse('crear_orden', args=[reserva.pk]), {
            'descripcion': 'x', 'tiempo_planificado_min': 60})
        self.assertEqual(respuesta.status_code, 404)

    def _cerrar(self, orden, minutos=120):
        return self.client.post(reverse('cerrar_orden', args=[orden.pk]), {
            'tiempo_real_min':      minutos,
            'tiempo_parada_min':    0,
            'unidades_producidas':  10,
            'unidades_sin_defecto': 10,
            'resultado':            'OK',
        })

    def test_cerrar_orden_completa_todo_el_ciclo(self):
        reserva = crear_reserva(self.tecnico, self.maquina, estado='APROBADA')
        orden = crear_orden_trabajo(reserva=reserva)
        self._cerrar(orden, minutos=120)
        orden.refresh_from_db()
        reserva.refresh_from_db()
        self.maquina.refresh_from_db()
        self.assertEqual(orden.estado, 'FINALIZADA')
        self.assertEqual(reserva.estado, 'COMPLETADA')
        self.assertEqual(self.maquina.horas_acumuladas, Decimal('2.00'))

    def test_cerrar_orden_con_certificacion_vencida_a_mitad_del_trabajo(self):
        """Regresión del 500 en cerrar_orden (2026-06-17)."""
        reserva = crear_reserva(self.tecnico, self.maquina, estado='EN_USO')
        orden = crear_orden_trabajo(reserva=reserva)
        from tpm.models import CertificacionUsuario
        CertificacionUsuario.objects.filter(usuario=self.tecnico).update(
            fecha_vencimiento=timezone.now().date() - timedelta(days=1))
        respuesta = self._cerrar(orden)
        self.assertEqual(respuesta.status_code, 302)  # nada de 500
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, 'COMPLETADA')

    def test_cerrar_dos_veces_no_duplica_horas(self):
        reserva = crear_reserva(self.tecnico, self.maquina, estado='APROBADA')
        orden = crear_orden_trabajo(reserva=reserva)
        self._cerrar(orden, minutos=60)
        self._cerrar(orden, minutos=60)  # segunda vez debe rechazarse
        self.maquina.refresh_from_db()
        self.assertEqual(self.maquina.horas_acumuladas, Decimal('1.00'))

    def test_registrar_consumo_descuenta_stock(self):
        from inventario.models import Material
        material = Material.objects.create(
            codigo='MAT-V01', nombre='Refrigerante', tipo='PRODUCCION',
            stock_actual=Decimal('10.00'), stock_minimo=Decimal('1.00'))
        orden = crear_orden_trabajo(usuario=self.tecnico, maquina=self.maquina)
        self.client.post(reverse('registrar_consumo', args=[orden.pk]), {
            'material_id': material.pk, 'cantidad': '4'})
        material.refresh_from_db()
        self.assertEqual(material.stock_actual, Decimal('6.00'))

    def test_consumo_mayor_al_stock_es_rechazado(self):
        from inventario.models import Material
        material = Material.objects.create(
            codigo='MAT-V02', nombre='Aceite', tipo='PRODUCCION',
            stock_actual=Decimal('2.00'), stock_minimo=Decimal('1.00'))
        orden = crear_orden_trabajo(usuario=self.tecnico, maquina=self.maquina)
        self.client.post(reverse('registrar_consumo', args=[orden.pk]), {
            'material_id': material.pk, 'cantidad': '5'})
        material.refresh_from_db()
        self.assertEqual(material.stock_actual, Decimal('2.00'))
        self.assertEqual(orden.consumos_material.count(), 0)


class OperadoresCertificadosEndpointTest(TestCase):
    """El selector de operadores del formulario de reservas consulta este
    endpoint JSON, que filtra por rol__nombre='OPERADOR' EXACTO."""

    def setUp(self):
        self.maquina = crear_maquina()
        self.client.force_login(crear_estudiante())

    def _operadores(self):
        respuesta = self.client.get(reverse('operadores_certificados'),
                                    {'maquina': self.maquina.pk})
        return respuesta.json()['operadores']

    def test_operador_con_rol_en_mayusculas_aparece(self):
        operador = crear_usuario(rol='OPERADOR')
        crear_certificacion(operador, self.maquina)
        self.assertEqual(len(self._operadores()), 1)

    def test_operador_sin_certificacion_no_aparece(self):
        crear_usuario(rol='OPERADOR')
        self.assertEqual(len(self._operadores()), 0)

    def test_operador_con_certificacion_vencida_no_aparece(self):
        operador = crear_usuario(rol='OPERADOR')
        crear_certificacion(operador, self.maquina, dias_vigencia=-1)
        self.assertEqual(len(self._operadores()), 0)

    def test_rol_con_otra_capitalizacion_tambien_deberia_aparecer(self):
        # Regresión BUG-03 (corregido 2026-07-07): el endpoint filtraba
        # rol__nombre='OPERADOR' exacto mientras permisos.py normaliza
        # mayúsculas, dejando inseleccionables a operadores con rol
        # 'Operador'. Ahora usa __iexact.
        operador = crear_usuario(rol='Operador')
        crear_certificacion(operador, self.maquina)
        self.assertEqual(
            len(self._operadores()), 1,
            'BUG-03: el filtro por nombre exacto de rol deja fuera a '
            'operadores con rol escrito distinto (Operador vs OPERADOR).')
