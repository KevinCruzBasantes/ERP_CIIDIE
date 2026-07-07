"""Matriz de control de acceso: qué roles pueden abrir cada vista protegida.

Cada caso hace GET a la URL con cada rol: si el rol está permitido se espera
200; si no, la vista debe redirigir (302) con mensaje de error.
"""
from django.test import TestCase
from django.urls import reverse

from testing_comun import crear_admin, crear_estudiante, crear_operador, crear_tecnico


class MatrizDeAccesosTest(TestCase):

    # (nombre_url, roles con acceso)
    CASOS = [
        ('lista_usuarios',       {'admin'}),
        ('crear_usuario',        {'admin'}),
        ('crear_maquina',        {'admin'}),
        ('crear_material',       {'admin', 'tecnico'}),
        ('crear_mantenimiento',  {'admin', 'tecnico'}),
        ('crear_certificacion',  {'admin', 'tecnico'}),
        ('crear_item_checklist', {'admin', 'tecnico'}),
        ('crear_codigo_parada',  {'admin', 'tecnico'}),
    ]

    @classmethod
    def setUpTestData(cls):
        cls.usuarios = {
            'admin':      crear_admin(),
            'tecnico':    crear_tecnico(),
            'estudiante': crear_estudiante(),
            'operador':   crear_operador(),
        }

    def test_matriz_de_accesos(self):
        for nombre_url, permitidos in self.CASOS:
            for rol, usuario in self.usuarios.items():
                with self.subTest(url=nombre_url, rol=rol):
                    self.client.force_login(usuario)
                    respuesta = self.client.get(reverse(nombre_url))
                    if rol in permitidos:
                        self.assertEqual(
                            respuesta.status_code, 200,
                            f'{rol} debería poder abrir {nombre_url}')
                    else:
                        self.assertEqual(
                            respuesta.status_code, 302,
                            f'{rol} NO debería poder abrir {nombre_url}')
