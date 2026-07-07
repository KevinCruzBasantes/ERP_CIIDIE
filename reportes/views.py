from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from usuarios.permisos import es_admin_o_tecnico
from .models import ReporteGenerado
from .services import (
    generar_reporte_excel,
    hoja_alertas,
    hoja_bitacora_mantenimiento,
    hoja_bitacora_operarios,
    hoja_certificaciones,
    hoja_consumos,
    hoja_incidentes,
    hoja_inspecciones,
    hoja_mantenimientos,
    hoja_materiales,
    hoja_oee,
    hoja_ordenes_mantenimiento,
    hoja_pareto,
    hoja_reservas,
    hojas_backup,
    hojas_piezas,
    hojas_resumen,
)


# Tarjetas de la página de reportes — la plantilla las recorre en un bucle.
TARJETAS = [
    {
        'titulo': 'Resumen ejecutivo', 'badge': 'Excel · 6 hojas',
        'url': 'reporte_resumen', 'boton': 'Descargar resumen', 'fechas': False,
        'descripcion': 'Vista general del sistema: KPIs, máquinas más utilizadas, '
                       'stock bajo, mantenimientos pendientes, alertas activas y '
                       'certificaciones por vencer.',
    },
    {
        'titulo': 'Mantenimiento', 'badge': 'Excel · 3 hojas',
        'url': 'reporte_mantenimiento', 'boton': 'Descargar mantenimiento', 'fechas': True,
        'descripcion': 'Órdenes de mantenimiento con origen, responsables y costos; '
                       'historial de mantenimientos y bitácora de mantenimiento. '
                       'Filtra por período de fechas.',
    },
    {
        'titulo': 'Producción y uso', 'badge': 'Excel · 5 hojas',
        'url': 'reporte_produccion', 'boton': 'Descargar producción', 'fechas': True,
        'descripcion': 'Reservas y órdenes de trabajo, bitácora de operarios, Pareto '
                       'de paradas, registros OEE (por mes) e inspecciones diarias TPM.',
    },
    {
        'titulo': 'Inventario y piezas', 'badge': 'Excel · 5 hojas',
        'url': 'reporte_inventario', 'boton': 'Descargar inventario', 'fechas': True,
        'descripcion': 'Materiales con stock y costos, historial de consumos, despiece '
                       'por máquina, transferencias y reasignaciones. Las fechas filtran '
                       'consumos y movimientos de piezas.',
    },
    {
        'titulo': 'Seguridad y personal', 'badge': 'Excel · 3 hojas',
        'url': 'reporte_seguridad', 'boton': 'Descargar seguridad', 'fechas': True,
        'descripcion': 'Incidentes y condiciones de riesgo, historial de alertas con su '
                       'ciclo de vida y certificaciones de usuarios. Las fechas filtran '
                       'incidentes y alertas.',
    },
    {
        'titulo': 'Respaldo completo', 'badge': 'Excel · todas las tablas',
        'url': 'reporte_backup', 'boton': 'Descargar respaldo', 'fechas': False,
        'descripcion': 'Volcado de todas las tablas de la base de datos, una hoja por '
                       'tabla con hoja índice. Copia de seguridad en formato Excel.',
    },
]


def _sin_permiso(request):
    """Guard de rol compartido por todas las vistas de reportes."""
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para acceder a reportes.')
        return redirect('dashboard_general')
    return None


def _vista_generar(request, *, tipo, nombre_base, hojas_fn,
                   usa_fechas=True, observaciones=''):
    """Patrón común de las vistas de generación: guard, POST-only, fechas."""
    denegado = _sin_permiso(request)
    if denegado:
        return denegado
    if request.method != 'POST':
        return redirect('lista_reportes')

    fecha_inicio = (request.POST.get('fecha_inicio') or None) if usa_fechas else None
    fecha_fin = (request.POST.get('fecha_fin') or None) if usa_fechas else None

    return generar_reporte_excel(
        request, tipo=tipo, nombre_base=nombre_base,
        hojas=hojas_fn(fecha_inicio, fecha_fin),
        fecha_inicio=fecha_inicio, fecha_fin=fecha_fin,
        observaciones=observaciones,
    )


@login_required(login_url='login')
def lista_reportes(request):
    denegado = _sin_permiso(request)
    if denegado:
        return denegado

    reportes = ReporteGenerado.objects.select_related('generado_por').all()[:50]
    return render(request, 'reportes/lista_reportes.html', {
        'reportes': reportes,
        'tarjetas': TARJETAS,
    })


@login_required(login_url='login')
def generar_resumen(request):
    return _vista_generar(
        request, tipo='RESUMEN', nombre_base='resumen_ejecutivo',
        hojas_fn=lambda fi, ff: hojas_resumen(), usa_fechas=False,
    )


@login_required(login_url='login')
def generar_mantenimiento(request):
    return _vista_generar(
        request, tipo='MANTENIMIENTO', nombre_base='mantenimiento',
        hojas_fn=lambda fi, ff: [
            hoja_ordenes_mantenimiento(fi, ff),
            hoja_mantenimientos(fi, ff),
            hoja_bitacora_mantenimiento(fi, ff),
        ],
    )


@login_required(login_url='login')
def generar_produccion(request):
    return _vista_generar(
        request, tipo='PRODUCCION', nombre_base='produccion_uso',
        hojas_fn=lambda fi, ff: [
            hoja_reservas(fi, ff),
            hoja_bitacora_operarios(fi, ff),
            hoja_pareto(fi, ff),
            hoja_oee(fi, ff),
            hoja_inspecciones(fi, ff),
        ],
    )


@login_required(login_url='login')
def generar_inventario(request):
    return _vista_generar(
        request, tipo='INVENTARIO', nombre_base='inventario_piezas',
        hojas_fn=lambda fi, ff: [hoja_materiales(), hoja_consumos(fi, ff)]
                                + hojas_piezas(fi, ff),
    )


@login_required(login_url='login')
def generar_seguridad(request):
    return _vista_generar(
        request, tipo='SEGURIDAD', nombre_base='seguridad_personal',
        hojas_fn=lambda fi, ff: [
            hoja_incidentes(fi, ff),
            hoja_alertas(fi, ff),
            hoja_certificaciones(),
        ],
    )


@login_required(login_url='login')
def generar_backup(request):
    return _vista_generar(
        request, tipo='BACKUP', nombre_base='respaldo_completo',
        hojas_fn=lambda fi, ff: hojas_backup(), usa_fechas=False,
        observaciones='Volcado completo de todas las tablas del sistema',
    )
