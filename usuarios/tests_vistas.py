from django.test import TestCase
from django.urls import reverse

from testing_comun import (
    crear_admin,
    crear_estudiante,
    crear_maquina,
    crear_operador,
    crear_reserva,
    crear_tecnico,
    crear_usuario,
)
from usuarios.models import Usuario


class LoginTest(TestCase):

    def test_admin_entra_y_va_a_su_dashboard(self):
        crear_admin(username='jefe')
        respuesta = self.client.post(reverse('login'), {
            'username': 'jefe', 'password': 'clave-pruebas-123'})
        self.assertRedirects(respuesta, reverse('dashboard_admin'))

    def test_tecnico_va_al_dashboard_tecnico(self):
        crear_tecnico(username='tec')
        respuesta = self.client.post(reverse('login'), {
            'username': 'tec', 'password': 'clave-pruebas-123'})
        self.assertRedirects(respuesta, reverse('dashboard_tecnico'))

    def test_estudiante_puede_entrar_con_su_cedula(self):
        estudiante = crear_estudiante(username='est1')
        respuesta = self.client.post(reverse('login'), {
            'username': estudiante.cedula, 'password': 'clave-pruebas-123'})
        self.assertRedirects(respuesta, reverse('dashboard_general'))

    def test_cuenta_suspendida_no_puede_entrar(self):
        crear_tecnico(username='castigado', estado='SUSPENDIDO')
        respuesta = self.client.post(reverse('login'), {
            'username': 'castigado', 'password': 'clave-pruebas-123'})
        self.assertEqual(respuesta.status_code, 200)  # se queda en el login
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_password_incorrecta_no_entra(self):
        crear_tecnico(username='tec')
        respuesta = self.client.post(reverse('login'), {
            'username': 'tec', 'password': 'incorrecta'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_anonimo_es_redirigido_al_login(self):
        respuesta = self.client.get(reverse('lista_usuarios'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('login'), respuesta.url)


class GestionUsuariosTest(TestCase):

    def setUp(self):
        self.admin = crear_admin()
        self.client.force_login(self.admin)

    def test_admin_ve_la_lista_de_usuarios(self):
        respuesta = self.client.get(reverse('lista_usuarios'))
        self.assertEqual(respuesta.status_code, 200)

    def test_tecnico_no_gestiona_usuarios(self):
        self.client.force_login(crear_tecnico())
        respuesta = self.client.get(reverse('lista_usuarios'))
        self.assertEqual(respuesta.status_code, 302)

    def test_cambiar_estado_de_usuario(self):
        objetivo = crear_usuario()
        self.client.post(reverse('cambiar_estado_usuario', args=[objetivo.pk]),
                         {'estado': 'SUSPENDIDO'})
        objetivo.refresh_from_db()
        self.assertEqual(objetivo.estado, 'SUSPENDIDO')

    def test_estado_invalido_no_se_aplica(self):
        objetivo = crear_usuario()
        self.client.post(reverse('cambiar_estado_usuario', args=[objetivo.pk]),
                         {'estado': 'HACKEADO'})
        objetivo.refresh_from_db()
        self.assertEqual(objetivo.estado, 'ACTIVO')

    def test_eliminar_usuario_conserva_sus_reservas_sin_dueno(self):
        tecnico = crear_tecnico()
        maquina = crear_maquina()
        reserva = crear_reserva(tecnico, maquina)
        respuesta = self.client.post(reverse('eliminar_usuario', args=[tecnico.pk]))
        self.assertRedirects(respuesta, reverse('lista_usuarios'))
        self.assertFalse(Usuario.objects.filter(pk=tecnico.pk).exists())
        reserva.refresh_from_db()  # usuario es SET_NULL: la reserva sobrevive
        self.assertIsNone(reserva.usuario)

    def test_no_puede_eliminarse_a_si_mismo(self):
        self.client.post(reverse('eliminar_usuario', args=[self.admin.pk]))
        self.assertTrue(Usuario.objects.filter(pk=self.admin.pk).exists())


class RestriccionEstudianteMiddlewareTest(TestCase):
    """El middleware limita a los estudiantes a /reservas/ y su panel.
    Regresión: estos accesos deben seguir bloqueados."""

    def setUp(self):
        self.client.force_login(crear_estudiante())

    def test_estudiante_no_ve_dashboards_de_otros_roles(self):
        for url in ('dashboard_admin', 'dashboard_tecnico', 'dashboard_operador'):
            with self.subTest(url=url):
                respuesta = self.client.get(reverse(url))
                self.assertRedirects(respuesta, reverse('dashboard_general'))

    def test_estudiante_no_entra_a_otros_modulos(self):
        for url in ('lista_maquinas', 'lista_materiales', 'lista_mantenimientos',
                    'dashboard_tpm', 'lista_usuarios'):
            with self.subTest(url=url):
                respuesta = self.client.get(reverse(url))
                self.assertRedirects(respuesta, reverse('dashboard_general'))

    def test_estudiante_si_puede_usar_reservas(self):
        respuesta = self.client.get(reverse('lista_reservas'))
        self.assertEqual(respuesta.status_code, 200)


class CierreSesionPorInactividadTest(TestCase):
    """La sesión se cierra sola tras SESION_INACTIVIDAD_MINUTOS sin actividad."""

    def setUp(self):
        self.tecnico = crear_tecnico()
        self.client.force_login(self.tecnico)

    def _envejecer_sesion(self, minutos):
        from django.utils import timezone
        sesion = self.client.session
        sesion['ultima_actividad'] = timezone.now().timestamp() - minutos * 60
        sesion.save()

    def test_sesion_inactiva_se_cierra_y_redirige_al_login(self):
        self._envejecer_sesion(31)
        respuesta = self.client.get(reverse('dashboard_tecnico'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('login'), respuesta.url)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_sesion_activa_no_se_toca(self):
        self._envejecer_sesion(29)
        respuesta = self.client.get(reverse('dashboard_tecnico'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('_auth_user_id', self.client.session)

    def test_cada_peticion_refresca_el_contador(self):
        self._envejecer_sesion(20)
        self.client.get(reverse('dashboard_tecnico'))  # actividad: se refresca
        self._respuesta_previa = self.client.session['ultima_actividad']
        from django.utils import timezone
        self.assertAlmostEqual(
            self.client.session['ultima_actividad'],
            timezone.now().timestamp(), delta=10)

    def test_la_primera_peticion_tras_el_login_marca_actividad(self):
        respuesta = self.client.get(reverse('dashboard_tecnico'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('ultima_actividad', self.client.session)


class DashboardsPorRolTest(TestCase):
    """Regresión BUG-04 (corregido 2026-07-07): los dashboards admin/técnico
    solo tenían @login_required; un operador o un usuario sin rol podía
    abrirlos por URL directa. Ahora exigen es_admin_o_tecnico."""

    def test_operador_no_deberia_ver_dashboard_admin(self):
        self.client.force_login(crear_operador())
        respuesta = self.client.get(reverse('dashboard_admin'))
        self.assertNotEqual(
            respuesta.status_code, 200,
            'BUG-04: un operador puede abrir el dashboard de administración.')

    def test_operador_no_deberia_ver_dashboard_tecnico(self):
        self.client.force_login(crear_operador())
        respuesta = self.client.get(reverse('dashboard_tecnico'))
        self.assertNotEqual(
            respuesta.status_code, 200,
            'BUG-04: un operador puede abrir el dashboard técnico.')

    def test_usuario_sin_rol_no_deberia_ver_dashboard_admin(self):
        self.client.force_login(crear_usuario())
        respuesta = self.client.get(reverse('dashboard_admin'))
        self.assertNotEqual(
            respuesta.status_code, 200,
            'BUG-04: un usuario sin rol puede abrir el dashboard de administración.')
