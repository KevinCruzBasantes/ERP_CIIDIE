from datetime import time

from django.core.exceptions import ValidationError
from django.test import TestCase

from testing_comun import crear_operador, crear_rol, crear_usuario
from usuarios.models import DisponibilidadOperador
from usuarios.permisos import es_admin, es_admin_o_tecnico, es_estudiante, es_operador


class PermisosPorRolTest(TestCase):
    """Matriz de roles contra las cuatro funciones de permisos.

    Incluye las variantes con/sin tilde y mayúsculas — regresión del bug
    de 2026-06-16 donde 'TÉCNICO' no coincidía con 'tecnico'.
    """

    CASOS = [
        # (nombre_rol, es_admin, es_admin_o_tecnico, es_estudiante, es_operador)
        ('Administrador', True,  True,  False, False),
        ('ADMINISTRADOR', True,  True,  False, False),
        ('PhD',           True,  True,  False, False),
        ('Técnico',       False, True,  False, False),
        ('TECNICO',       False, True,  False, False),
        ('TÉCNICO',       False, True,  False, False),  # regresión tilde+mayúsculas
        ('Tecnico',       False, True,  False, False),
        ('Ingeniero',     False, True,  False, False),
        ('Estudiante',    False, False, True,  False),
        ('ESTUDIANTE',    False, False, True,  False),
        ('Operador',      False, False, False, True),
        ('OPERADOR',      False, False, False, True),
    ]

    def test_matriz_de_roles(self):
        for nombre, admin, admin_tec, estudiante, operador in self.CASOS:
            with self.subTest(rol=nombre):
                usuario = crear_usuario(rol=nombre)
                self.assertEqual(es_admin(usuario), admin)
                self.assertEqual(es_admin_o_tecnico(usuario), admin_tec)
                self.assertEqual(es_estudiante(usuario), estudiante)
                self.assertEqual(es_operador(usuario), operador)

    def test_usuario_sin_rol_no_tiene_permisos(self):
        usuario = crear_usuario()
        self.assertFalse(es_admin(usuario))
        self.assertFalse(es_admin_o_tecnico(usuario))
        self.assertFalse(es_estudiante(usuario))
        self.assertFalse(es_operador(usuario))

    def test_superuser_es_admin_sin_importar_rol(self):
        superuser = crear_usuario(superuser=True)
        self.assertTrue(es_admin(superuser))
        self.assertTrue(es_admin_o_tecnico(superuser))
        self.assertFalse(es_estudiante(superuser))
        self.assertFalse(es_operador(superuser))

    def test_superuser_con_rol_estudiante_sigue_siendo_admin(self):
        # is_superuser se evalúa antes que el rol
        superuser = crear_usuario(superuser=True)
        superuser.rol = crear_rol('Estudiante')
        superuser.save(update_fields=['rol'])
        self.assertTrue(es_admin(superuser))
        self.assertFalse(es_estudiante(superuser))


class UsuarioModelTest(TestCase):

    def test_esta_activo_segun_estado(self):
        usuario = crear_usuario()
        self.assertTrue(usuario.esta_activo)
        usuario.estado = 'SUSPENDIDO'
        self.assertFalse(usuario.esta_activo)
        usuario.estado = 'INACTIVO'
        self.assertFalse(usuario.esta_activo)

    def test_str_usa_nombre_completo_o_username(self):
        usuario = crear_usuario(username='jperez')
        self.assertEqual(str(usuario), 'jperez')
        usuario.first_name, usuario.last_name = 'Juan', 'Pérez'
        self.assertEqual(str(usuario), 'Juan Pérez')


class DisponibilidadOperadorTest(TestCase):

    def setUp(self):
        self.operador = crear_operador()

    def test_bloque_valido_se_guarda(self):
        bloque = DisponibilidadOperador.objects.create(
            operador=self.operador, dia_semana=0,
            hora_inicio=time(8, 0), hora_fin=time(12, 0),
        )
        self.assertIsNotNone(bloque.pk)

    def test_hora_fin_igual_a_inicio_es_invalida(self):
        with self.assertRaises(ValidationError):
            DisponibilidadOperador.objects.create(
                operador=self.operador, dia_semana=0,
                hora_inicio=time(8, 0), hora_fin=time(8, 0),
            )

    def test_hora_fin_menor_a_inicio_es_invalida(self):
        with self.assertRaises(ValidationError):
            DisponibilidadOperador.objects.create(
                operador=self.operador, dia_semana=0,
                hora_inicio=time(12, 0), hora_fin=time(8, 0),
            )
