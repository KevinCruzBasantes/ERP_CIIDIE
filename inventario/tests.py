from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from testing_comun import crear_usuario
from inventario.models import ConsumoMaterial, Material


def crear_material(**extra):
    datos = dict(codigo='MAT-001', nombre='Aceite hidráulico',
                 tipo='MANTENIMIENTO', stock_actual=Decimal('10.00'),
                 stock_minimo=Decimal('2.00'))
    datos.update(extra)
    return Material.objects.create(**datos)


class MaterialModelTest(TestCase):

    def test_stock_bajo_incluye_el_limite(self):
        material = crear_material(stock_actual=Decimal('2.00'))
        self.assertTrue(material.stock_bajo)   # igual al mínimo cuenta como bajo
        material.stock_actual = Decimal('2.01')
        self.assertFalse(material.stock_bajo)


class ConsumoMaterialTest(TestCase):

    def setUp(self):
        self.material = crear_material()
        self.usuario = crear_usuario()

    def test_consumo_descuenta_stock(self):
        ConsumoMaterial.objects.create(
            material=self.material, cantidad=Decimal('3.00'),
            realizado_por=self.usuario,
        )
        self.material.refresh_from_db()
        self.assertEqual(self.material.stock_actual, Decimal('7.00'))

    def test_clean_rechaza_consumo_mayor_al_stock(self):
        consumo = ConsumoMaterial(
            material=self.material, cantidad=Decimal('11.00'),
        )
        with self.assertRaises(ValidationError):
            consumo.full_clean()

    def test_save_directo_tambien_protege_el_stock(self):
        with self.assertRaises(ValueError):
            ConsumoMaterial.objects.create(
                material=self.material, cantidad=Decimal('99.00'),
            )
        self.material.refresh_from_db()
        self.assertEqual(self.material.stock_actual, Decimal('10.00'))

    def test_editar_un_consumo_no_vuelve_a_descontar(self):
        consumo = ConsumoMaterial.objects.create(
            material=self.material, cantidad=Decimal('3.00'),
        )
        consumo.observacion = 'corrección de nota'
        consumo.save()
        self.material.refresh_from_db()
        self.assertEqual(self.material.stock_actual, Decimal('7.00'))
