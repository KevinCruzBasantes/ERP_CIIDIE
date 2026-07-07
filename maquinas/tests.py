from django.test import TestCase

from testing_comun import crear_maquina, crear_usuario
from maquinas.models import Pieza, TransferenciaPieza


class MaquinaModelTest(TestCase):

    def test_disponible_para_reserva_solo_si_operativa(self):
        maquina = crear_maquina()
        self.assertTrue(maquina.disponible_para_reserva)
        maquina.estado = 'MANTENIMIENTO'
        self.assertFalse(maquina.disponible_para_reserva)
        maquina.estado = 'BAJA'
        self.assertFalse(maquina.disponible_para_reserva)


class PiezaModelTest(TestCase):

    def setUp(self):
        self.maquina = crear_maquina(nombre='Fresadora')
        self.ensamble = Pieza.objects.create(
            maquina=self.maquina, nombre='Eje X', es_ensamble=True,
        )

    def test_stock_bajo_en_pieza_individual(self):
        pieza = Pieza.objects.create(
            maquina=self.maquina, ensamble=self.ensamble, nombre='Motor',
            stock_repuestos=2, stock_minimo_repuestos=2,
        )
        self.assertTrue(pieza.stock_bajo)   # igual al mínimo cuenta como bajo
        pieza.stock_repuestos = 3
        self.assertFalse(pieza.stock_bajo)

    def test_un_ensamble_nunca_reporta_stock_bajo(self):
        self.ensamble.stock_repuestos = 0
        self.ensamble.stock_minimo_repuestos = 5
        self.assertFalse(self.ensamble.stock_bajo)

    def test_ruta_completa_con_y_sin_ensamble(self):
        pieza = Pieza.objects.create(
            maquina=self.maquina, ensamble=self.ensamble, nombre='Motor',
        )
        self.assertEqual(pieza.get_ruta_completa(), 'Fresadora › Eje X › Motor')
        self.assertEqual(self.ensamble.get_ruta_completa(), 'Fresadora › Eje X')

    def test_str_de_ensamble_y_pieza(self):
        pieza = Pieza.objects.create(
            maquina=self.maquina, ensamble=self.ensamble, nombre='Motor',
        )
        self.assertIn('[Ensamble]', str(self.ensamble))
        self.assertEqual(str(pieza), 'Eje X › Motor')


class TransferenciaPiezaTest(TestCase):

    def setUp(self):
        self.maquina_a = crear_maquina()
        self.maquina_b = crear_maquina()
        self.pieza = Pieza.objects.create(maquina=self.maquina_a, nombre='Rodamiento')

    def test_str_con_ambas_maquinas(self):
        transferencia = TransferenciaPieza.objects.create(
            pieza=self.pieza, maquina_origen=self.maquina_a,
            maquina_destino=self.maquina_b,
        )
        self.assertIn('Rodamiento', str(transferencia))

    def test_str_sin_maquina_origen_no_debe_reventar(self):
        # Regresión BUG-01 (corregido 2026-07-07): __str__ hacía
        # self.maquina_origen.codigo sin proteger el None (transferencias
        # desde/hacia bodega) y reventaba con AttributeError.
        transferencia = TransferenciaPieza.objects.create(
            pieza=self.pieza, maquina_origen=None, maquina_destino=self.maquina_b,
        )
        try:
            resultado = str(transferencia)
        except AttributeError:
            self.fail('BUG-01: TransferenciaPieza.__str__ revienta cuando '
                      'maquina_origen es None (campo permitido como NULL).')
        self.assertIn('Rodamiento', resultado)
