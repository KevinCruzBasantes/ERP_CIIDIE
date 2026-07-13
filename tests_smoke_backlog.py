"""Smoke test temporal de los fixes del backlog de testeo 2026-07-13.

Se corre con:
    manage.py test tests_smoke_backlog

Cubre: MAQ-02, CERT-02/03, INC-02, INS-07, OM-02, INV-06, CHK-02, DASH-03.
(Archivo desechable: puede borrarse después de validar en el servidor.)
"""
from django.test import TestCase, Client
from django.utils import timezone

from usuarios.models import Usuario, Rol
from maquinas.models import Maquina, Pieza
from inventario.models import Material
from tpm.models import Incidente, ItemChecklistInspeccion, InspeccionDiaria, HallazgoInspeccion
from mantenimiento.models import OrdenMantenimiento


class SmokeBacklog20260713(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.rol_admin, _ = Rol.objects.get_or_create(nombre='ADMINISTRADOR')
        cls.rol_op, _    = Rol.objects.get_or_create(nombre='OPERADOR')
        cls.rol_est, _   = Rol.objects.get_or_create(nombre='ESTUDIANTE')
        cls.admin = Usuario.objects.create_user(
            username='adm_smoke', password='x', cedula='9000000001',
            rol=cls.rol_admin, estado='ACTIVO')
        cls.oper = Usuario.objects.create_user(
            username='op_smoke', password='x', cedula='9000000002',
            rol=cls.rol_op, estado='ACTIVO')
        cls.est = Usuario.objects.create_user(
            username='est_smoke', password='x', cedula='9000000003',
            rol=cls.rol_est, estado='ACTIVO')
        cls.maq = Maquina.objects.create(
            nombre='M1', codigo='M-SMOKE-001', ubicacion='Lab', estado='OPERATIVA',
            fabricante='OPTIMUM', modelo='F210HSC')

    def test_vistas_modificadas_renderizan(self):
        mat_activo = Material.objects.create(
            codigo='MAT-S1', nombre='Aceite', tipo='AMBOS', stock_actual=10, stock_minimo=1)
        mat_inactivo = Material.objects.create(
            codigo='MAT-S2', nombre='Grasa', tipo='AMBOS', activo=False)
        item = ItemChecklistInspeccion.objects.create(
            fabricante='OPTIMUM', modelo_maquina='F210HSC', nombre='Chequeo X')
        om = OrdenMantenimiento.objects.create(
            maquina=self.maq, tipo='CORRECTIVO', titulo='OM prueba',
            fecha_programada=timezone.now().date())
        Incidente.objects.create(
            maquina=self.maq, tipo='ANOMALIA', severidad='BAJA', descripcion='x',
            reportado_por=self.oper, fecha_ocurrencia=timezone.now())

        c = Client()
        c.force_login(self.admin)
        rutas = [
            '/maquinas/crear/',
            f'/maquinas/{self.maq.pk}/',
            '/tpm/certificaciones/crear/',
            '/tpm/incidentes/',
            '/tpm/checklist-items/crear/',
            f'/tpm/checklist-items/{item.pk}/editar/',
            '/mantenimiento/ordenes/crear/',
            f'/mantenimiento/ordenes/{om.pk}/editar/',
            '/inventario/',
            f'/inventario/{mat_activo.pk}/',
            f'/inventario/{mat_inactivo.pk}/',
        ]
        for url in rutas:
            with self.subTest(url=url):
                self.assertEqual(c.get(url).status_code, 200)

        # INV-06: reactivar material
        r = c.post(f'/inventario/{mat_inactivo.pk}/reactivar/')
        mat_inactivo.refresh_from_db()
        self.assertEqual(r.status_code, 302)
        self.assertTrue(mat_inactivo.activo)

        # INC-02: el listado enlaza al detalle
        incidente = Incidente.objects.get(descripcion='x')
        contenido = c.get('/tpm/incidentes/').content.decode()
        self.assertIn(f'/tpm/incidentes/{incidente.pk}/', contenido)

    def test_dash_operador_muestra_incidentes(self):
        Incidente.objects.create(
            maquina=self.maq, tipo='ANOMALIA', severidad='BAJA', descripcion='algo raro',
            reportado_por=self.oper, fecha_ocurrencia=timezone.now())
        c = Client()
        c.force_login(self.oper)
        r = c.get('/dashboard/operador/')
        self.assertEqual(r.status_code, 200)
        contenido = r.content.decode()
        self.assertIn('Mis incidentes reportados', contenido)
        self.assertIn('M1', contenido)
        self.assertIn('Reservas canceladas', contenido)

    def test_cert_form_sin_estudiantes_y_usuario_bloqueado_al_editar(self):
        from tpm.forms import CertificacionForm
        form = CertificacionForm(usuario_actual=self.admin)
        usuarios_dd = list(form.fields['usuario'].queryset)
        self.assertNotIn(self.est, usuarios_dd)
        self.assertIn(self.oper, usuarios_dd)

        # Al editar, el campo usuario queda deshabilitado
        from tpm.models import CertificacionUsuario
        hoy = timezone.now().date()
        cert = CertificacionUsuario.objects.create(
            usuario=self.oper, maquina=self.maq, otorgado_por=self.admin,
            fecha_otorgamiento=hoy, fecha_vencimiento=hoy + timezone.timedelta(days=365))
        form = CertificacionForm(instance=cert, usuario_actual=self.admin)
        self.assertTrue(form.fields['usuario'].disabled)

    def test_maquina_form_responsable_solo_jerarquia_alta(self):
        from maquinas.forms import MaquinaForm
        form = MaquinaForm()
        responsables = list(form.fields['responsable'].queryset)
        self.assertIn(self.admin, responsables)
        self.assertNotIn(self.oper, responsables)
        self.assertNotIn(self.est, responsables)

    def test_om_form_un_solo_responsable_jerarquia(self):
        from mantenimiento.forms import OrdenMantenimientoForm
        form = OrdenMantenimientoForm()
        self.assertNotIn('responsable_2', form.fields)
        self.assertNotIn('responsable_3', form.fields)
        responsables = list(form.fields['responsable_1'].queryset)
        self.assertIn(self.admin, responsables)
        self.assertNotIn(self.oper, responsables)
        self.assertNotIn(self.est, responsables)

    def test_item_checklist_ambito_desplegable(self):
        from tpm.forms import ItemChecklistForm
        form = ItemChecklistForm(data={
            'ambito': 'OPTIMUM|||F210HSC', 'nombre': 'Chequeo Y', 'es_critico': 'on'})
        self.assertTrue(form.is_valid(), form.errors)
        nuevo = form.save()
        self.assertEqual(nuevo.fabricante, 'OPTIMUM')
        self.assertEqual(nuevo.modelo_maquina, 'F210HSC')

        # Duplicado (mismo ámbito + nombre) se rechaza con error de form, no IntegrityError
        dup = ItemChecklistForm(data={
            'ambito': 'OPTIMUM|||F210HSC', 'nombre': 'Chequeo Y', 'es_critico': 'on'})
        self.assertFalse(dup.is_valid())

        # El ámbito ofrecido sale de las máquinas registradas
        form = ItemChecklistForm()
        valores = [v for v, _ in form.fields['ambito'].choices]
        self.assertIn('OPTIMUM|||F210HSC', valores)

    def test_eliminar_hallazgo_desactiva_om_automatica(self):
        insp = InspeccionDiaria.objects.create(
            maquina=self.maq, inspector=self.admin, fecha=timezone.now().date())
        hallazgo = HallazgoInspeccion.objects.create(
            inspeccion=insp, descripcion='grieta', prioridad='ALTA')
        om = OrdenMantenimiento.objects.get(hallazgo=hallazgo, origen='HALLAZGO')
        self.assertTrue(om.activo)

        c = Client()
        c.force_login(self.admin)
        r = c.post(f'/tpm/hallazgos/{hallazgo.pk}/eliminar/')
        self.assertEqual(r.status_code, 302)
        om.refresh_from_db()
        self.assertFalse(om.activo)
        self.assertFalse(HallazgoInspeccion.objects.filter(pk=hallazgo.pk).exists())
        # Y la máquina no queda atascada en MANTENIMIENTO
        self.maq.refresh_from_db()
        self.assertEqual(self.maq.estado, 'OPERATIVA')
