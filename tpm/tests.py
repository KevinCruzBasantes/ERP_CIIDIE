from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from testing_comun import (
    crear_certificacion,
    crear_codigo_parada,
    crear_maquina,
    crear_orden_trabajo,
    crear_tecnico,
    crear_usuario,
)
from tpm.models import (
    Alerta,
    CertificacionUsuario,
    InspeccionDiaria,
    ItemChecklistInspeccion,
    RegistroOEE,
    RespuestaChecklistInspeccion,
)


class CertificacionUsuarioTest(TestCase):

    def setUp(self):
        self.usuario = crear_usuario()
        self.maquina = crear_maquina()

    def test_vigente_incluye_el_dia_del_vencimiento(self):
        cert = crear_certificacion(self.usuario, self.maquina, dias_vigencia=0)
        self.assertTrue(cert.vigente)

    def test_vencida_ayer_no_es_vigente(self):
        cert = crear_certificacion(self.usuario, self.maquina, dias_vigencia=-1)
        self.assertFalse(cert.vigente)

    def test_dias_para_vencer(self):
        cert = crear_certificacion(self.usuario, self.maquina, dias_vigencia=10)
        self.assertEqual(cert.dias_para_vencer, 10)
        vencida = crear_certificacion(
            self.usuario, self.maquina, dias_vigencia=-5,
            fecha_otorgamiento=timezone.now().date() - timedelta(days=30))
        self.assertEqual(vencida.dias_para_vencer, -5)


class InspeccionDiariaTest(TestCase):

    def setUp(self):
        self.maquina = crear_maquina()
        self.inspector = crear_tecnico()

    def crear_inspeccion(self, **extra):
        datos = dict(maquina=self.maquina, inspector=self.inspector,
                     fecha=timezone.now().date())
        datos.update(extra)
        return InspeccionDiaria.objects.create(**datos)

    def test_inspeccion_limpia_queda_aprobada(self):
        inspeccion = self.crear_inspeccion()
        self.assertTrue(inspeccion.aprobada)
        self.assertEqual(Alerta.objects.count(), 0)

    def test_guardas_fallidas_reprueban(self):
        inspeccion = self.crear_inspeccion(guardas_seguridad_ok=False)
        self.assertFalse(inspeccion.aprobada)

    def test_ruidos_anormales_reprueban(self):
        inspeccion = self.crear_inspeccion(ruidos_anormales=True)
        self.assertFalse(inspeccion.aprobada)

    def test_item_critico_del_catalogo_reprueba_al_recalcular(self):
        inspeccion = self.crear_inspeccion()
        item = ItemChecklistInspeccion.objects.create(
            fabricante='OPTIMUM', modelo_maquina='F210HSC',
            nombre='Nivel de aceite dentro de rango', es_critico=True)
        RespuestaChecklistInspeccion.objects.create(
            inspeccion=inspeccion, item=item, ok=False)
        inspeccion.recalcular_aprobada()
        self.assertFalse(inspeccion.aprobada)

    def test_item_no_critico_fallido_no_reprueba(self):
        inspeccion = self.crear_inspeccion()
        item = ItemChecklistInspeccion.objects.create(
            fabricante='OPTIMUM', modelo_maquina='F210HSC',
            nombre='Limpieza de bandeja de virutas', es_critico=False)
        RespuestaChecklistInspeccion.objects.create(
            inspeccion=inspeccion, item=item, ok=False)
        inspeccion.recalcular_aprobada()
        self.assertTrue(inspeccion.aprobada)


class RegistroOEETest(TestCase):

    def test_oee_se_calcula_al_guardar(self):
        registro = RegistroOEE.objects.create(
            maquina=crear_maquina(), mes=6, anio=2026,
            disponibilidad=Decimal('90.00'),
            rendimiento=Decimal('80.00'),
            calidad=Decimal('95.00'),
        )
        self.assertEqual(registro.oee, Decimal('68.40'))


class AlertaModelTest(TestCase):

    def setUp(self):
        self.usuario = crear_tecnico()

    def crear_alerta(self, **extra):
        datos = dict(tipo='STOCK_BAJO', mensaje='Alerta de prueba')
        datos.update(extra)
        return Alerta.objects.create(**datos)

    def test_puede_generar_om_segun_tipo(self):
        self.assertTrue(self.crear_alerta(tipo='INSPECCION_FALLIDA').puede_generar_om)
        self.assertFalse(self.crear_alerta(tipo='CERTIFICACION_POR_VENCER').puede_generar_om)

    def test_titulo_om_sugerido_tiene_valor_por_defecto(self):
        alerta = self.crear_alerta(tipo='STOCK_BAJO')
        self.assertEqual(alerta.titulo_om_sugerido, 'Intervención correctiva')

    def test_marcar_vista_no_sobreescribe_la_primera_vista(self):
        alerta = self.crear_alerta()
        alerta.marcar_vista(self.usuario)
        primera_vista = alerta.vista_en
        otro = crear_tecnico()
        alerta.marcar_vista(otro)
        alerta.refresh_from_db()
        self.assertEqual(alerta.vista_por, self.usuario)
        self.assertEqual(alerta.vista_en, primera_vista)

    def test_resolver_completa_el_ciclo_de_vida(self):
        alerta = self.crear_alerta()
        alerta.resolver(self.usuario, nota='Se repuso el stock')
        alerta.refresh_from_db()
        self.assertTrue(alerta.resuelta)
        self.assertEqual(alerta.resuelta_por, self.usuario)
        self.assertEqual(alerta.nota_resolucion, 'Se repuso el stock')
        self.assertIsNotNone(alerta.resuelta_en)


class SignalsAlertasTest(TestCase):
    """Alertas generadas automáticamente por tpm/signals.py."""

    def setUp(self):
        self.maquina = crear_maquina()
        self.tecnico = crear_tecnico()

    def test_inspeccion_fallida_genera_alerta_critica_sin_duplicar(self):
        inspeccion = InspeccionDiaria.objects.create(
            maquina=self.maquina, inspector=self.tecnico,
            fecha=timezone.now().date(), guardas_seguridad_ok=False)
        alertas = Alerta.objects.filter(tipo='INSPECCION_FALLIDA')
        self.assertEqual(alertas.count(), 1)
        self.assertEqual(alertas.first().severidad, 'CRITICA')
        inspeccion.save()  # re-guardar no debe duplicar
        self.assertEqual(alertas.count(), 1)

    def test_incidente_con_mantenimiento_genera_alerta_solo_al_crear(self):
        from tpm.models import Incidente
        incidente = Incidente.objects.create(
            maquina=self.maquina, reportado_por=self.tecnico,
            tipo='ANOMALIA', severidad='ALTA', descripcion='Fuga de aceite',
            requiere_mantenimiento=True, fecha_ocurrencia=timezone.now())
        self.assertEqual(Alerta.objects.filter(tipo='INCIDENTE').count(), 1)
        incidente.save()
        self.assertEqual(Alerta.objects.filter(tipo='INCIDENTE').count(), 1)

    def test_incidente_sin_mantenimiento_no_genera_alerta(self):
        from tpm.models import Incidente
        Incidente.objects.create(
            maquina=self.maquina, reportado_por=self.tecnico,
            tipo='ANOMALIA', severidad='BAJA', descripcion='Observación menor',
            requiere_mantenimiento=False, fecha_ocurrencia=timezone.now())
        self.assertEqual(Alerta.objects.filter(tipo='INCIDENTE').count(), 0)

    def test_parada_no_planificada_genera_alerta(self):
        from reservas.models import RegistroParada
        from datetime import time
        ot = crear_orden_trabajo(usuario=self.tecnico, maquina=self.maquina)
        codigo = crear_codigo_parada(tipo='NO_PLANIFICADA')
        RegistroParada.objects.create(
            orden_trabajo=ot, codigo_parada=codigo,
            hora_inicio=time(10, 0), hora_fin=time(10, 30),
            descripcion_tecnica='Se trabó el husillo')
        self.assertEqual(
            Alerta.objects.filter(tipo='PARADA_NO_PLANIFICADA').count(), 1)

    def test_parada_planificada_no_genera_alerta(self):
        from reservas.models import RegistroParada
        from datetime import time
        ot = crear_orden_trabajo(usuario=self.tecnico, maquina=self.maquina)
        codigo = crear_codigo_parada(tipo='PLANIFICADA', categoria='OPERACION')
        RegistroParada.objects.create(
            orden_trabajo=ot, codigo_parada=codigo,
            hora_inicio=time(10, 0), hora_fin=time(10, 30),
            descripcion_tecnica='Cambio de herramienta programado')
        self.assertEqual(
            Alerta.objects.filter(tipo='PARADA_NO_PLANIFICADA').count(), 0)

    def test_bitacora_con_atencion_genera_alerta(self):
        from reservas.models import BitacoraOperario
        ot = crear_orden_trabajo(usuario=self.tecnico, maquina=self.maquina)
        BitacoraOperario.objects.create(
            orden_trabajo=ot, operario=self.tecnico,
            descripcion_trabajo='Vibración fuerte en eje Z',
            requiere_atencion=True)
        self.assertEqual(Alerta.objects.filter(tipo='BITACORA_ATENCION').count(), 1)

    def test_bitacora_normal_no_genera_alerta(self):
        from reservas.models import BitacoraOperario
        ot = crear_orden_trabajo(usuario=self.tecnico, maquina=self.maquina)
        BitacoraOperario.objects.create(
            orden_trabajo=ot, operario=self.tecnico,
            descripcion_trabajo='Todo normal')
        self.assertEqual(Alerta.objects.filter(tipo='BITACORA_ATENCION').count(), 0)
