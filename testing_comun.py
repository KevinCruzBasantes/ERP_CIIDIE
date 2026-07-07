"""Helpers compartidos por las suites de pruebas de todas las apps.

No es un módulo de tests (el runner no lo descubre): solo fábricas de
objetos con valores por defecto válidos, para que cada test declare
únicamente lo que le interesa.
"""
import itertools
from datetime import time, timedelta

from django.utils import timezone

_contador = itertools.count(1)


# ── Usuarios y roles ─────────────────────────────────────────────────────────

def crear_rol(nombre):
    from usuarios.models import Rol
    rol, _ = Rol.objects.get_or_create(nombre=nombre)
    return rol


def crear_usuario(username=None, rol=None, superuser=False, **extra):
    from usuarios.models import Usuario
    n = next(_contador)
    datos = dict(
        username=username or f'usuario{n}',
        cedula=str(1000000000 + n),
        password='clave-pruebas-123',
    )
    datos.update(extra)
    if superuser:
        return Usuario.objects.create_superuser(**datos)
    usuario = Usuario.objects.create_user(**datos)
    if rol:
        usuario.rol = crear_rol(rol) if isinstance(rol, str) else rol
        usuario.save(update_fields=['rol'])
    return usuario


def crear_admin(**kw):
    return crear_usuario(rol='Administrador', **kw)


def crear_tecnico(**kw):
    return crear_usuario(rol='Técnico', **kw)


def crear_estudiante(**kw):
    return crear_usuario(rol='Estudiante', **kw)


def crear_operador(**kw):
    return crear_usuario(rol='Operador', **kw)


# ── Máquinas y catálogo ──────────────────────────────────────────────────────

def crear_maquina(**extra):
    from maquinas.models import Maquina
    n = next(_contador)
    datos = dict(nombre=f'Máquina {n}', codigo=f'MAQ-{n:04d}', ubicacion='Laboratorio')
    datos.update(extra)
    return Maquina.objects.create(**datos)


def crear_codigo_parada(**extra):
    from maquinas.models import CodigoParada
    n = next(_contador)
    datos = dict(fabricante='OPTIMUM', modelo_maquina='F210HSC',
                 codigo=f'COD-{n:03d}', tipo='NO_PLANIFICADA',
                 categoria='MECANICA', subsistema='Motor principal')
    datos.update(extra)
    return CodigoParada.objects.create(**datos)


# ── TPM ──────────────────────────────────────────────────────────────────────

def crear_certificacion(usuario, maquina, dias_vigencia=365, **extra):
    from tpm.models import CertificacionUsuario
    hoy = timezone.now().date()
    datos = dict(usuario=usuario, maquina=maquina,
                 fecha_otorgamiento=hoy - timedelta(days=1),
                 fecha_vencimiento=hoy + timedelta(days=dias_vigencia))
    datos.update(extra)
    return CertificacionUsuario.objects.create(**datos)


# ── Reservas ─────────────────────────────────────────────────────────────────

def crear_reserva(usuario, maquina, *, con_certificacion=True, **extra):
    """Reserva válida mañana de 09:00 a 11:00. Certifica automáticamente al
    sujeto que Reserva.clean() exige (el operador si hay, si no el usuario),
    salvo que se pida lo contrario con con_certificacion=False."""
    from reservas.models import Reserva
    from tpm.models import CertificacionUsuario

    if con_certificacion:
        sujeto = extra.get('operador') or usuario
        hoy = timezone.now().date()
        if not CertificacionUsuario.objects.filter(
                usuario=sujeto, maquina=maquina, activo=True,
                fecha_vencimiento__gte=hoy).exists():
            crear_certificacion(sujeto, maquina)

    datos = dict(
        usuario=usuario, maquina=maquina,
        fecha=timezone.now().date() + timedelta(days=1),
        hora_inicio=time(9, 0), hora_fin=time(11, 0),
    )
    datos.update(extra)
    return Reserva.objects.create(**datos)


def crear_orden_trabajo(reserva=None, usuario=None, maquina=None, **extra):
    from reservas.models import OrdenTrabajo
    if reserva is None:
        reserva = crear_reserva(usuario, maquina)
    datos = dict(reserva=reserva, descripcion='Trabajo de prueba')
    datos.update(extra)
    return OrdenTrabajo.objects.create(**datos)
