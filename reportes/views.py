from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import F
from django.utils import timezone

from usuarios.permisos import es_admin_o_tecnico
from .models import ReporteGenerado
from .services import (
    ReporteService,
    fmt_fecha,
    fmt_fecha_hora,
    fmt_num,
    fmt_texto,
    fmt_usuario,
    generar_reporte_excel,
    si_no,
)
from inventario.models import Material
from mantenimiento.models import Mantenimiento


def _sin_permiso(request):
    """Guard de rol compartido por todas las vistas de reportes."""
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para acceder a reportes.')
        return redirect('dashboard_general')
    return None


@login_required(login_url='login')
def lista_reportes(request):
    from maquinas.models import Maquina
    from tpm.models import RegistroOEE

    denegado = _sin_permiso(request)
    if denegado:
        return denegado

    reportes = ReporteGenerado.objects.select_related('generado_por').all()[:50]
    context = {
        'reportes': reportes,
        'tipos': ReporteGenerado.TIPOS,
        'maquinas': Maquina.objects.order_by('nombre'),
        'anios_oee': RegistroOEE.objects.values_list('anio', flat=True)
                                        .distinct().order_by('-anio'),
    }
    return render(request, 'reportes/lista_reportes.html', context)


@login_required(login_url='login')
def generar_inventario(request):
    denegado = _sin_permiso(request)
    if denegado:
        return denegado
    if request.method != 'POST':
        return redirect('lista_reportes')

    encabezados = ['Código', 'Nombre', 'Tipo', 'Unidad', 'Stock actual',
                   'Stock mínimo', 'Estado stock', 'Proveedor', 'Costo unitario']

    filas = [
        [m.codigo, m.nombre, m.get_tipo_display(), m.unidad_medida,
         float(m.stock_actual), float(m.stock_minimo),
         'Stock bajo' if m.stock_bajo else 'OK',
         fmt_texto(m.proveedor), float(m.costo_unitario)]
        for m in Material.objects.filter(activo=True)
    ]

    return generar_reporte_excel(
        request, tipo='INVENTARIO', nombre_base='inventario',
        hojas=[('Inventario', encabezados, filas)],
    )


@login_required(login_url='login')
def generar_mantenimiento(request):
    denegado = _sin_permiso(request)
    if denegado:
        return denegado
    if request.method != 'POST':
        return redirect('lista_reportes')

    fecha_inicio = request.POST.get('fecha_inicio')
    fecha_fin = request.POST.get('fecha_fin')

    encabezados = ['#', 'Máquina', 'Código', 'Tipo', 'Estado', 'Prioridad',
                   'Fecha programada', 'Fecha inicio', 'Fecha fin',
                   'Horas trabajo', 'Costo', 'Responsable', 'Descripción']

    qs = Mantenimiento.objects.select_related('maquina', 'responsable')
    if fecha_inicio:
        qs = qs.filter(fecha_programada__gte=fecha_inicio)
    if fecha_fin:
        qs = qs.filter(fecha_programada__lte=fecha_fin)

    filas = [
        [m.pk, m.maquina.nombre, m.maquina.codigo, m.get_tipo_display(),
         m.get_estado_display(), m.get_prioridad_display(),
         fmt_fecha(m.fecha_programada), fmt_fecha_hora(m.fecha_inicio),
         fmt_fecha_hora(m.fecha_fin), float(m.horas_trabajo), float(m.costo),
         fmt_usuario(m.responsable), m.descripcion]
        for m in qs
    ]

    return generar_reporte_excel(
        request, tipo='MANTENIMIENTO', nombre_base='mantenimiento',
        hojas=[('Mantenimiento', encabezados, filas, 20)],
        fecha_inicio=fecha_inicio, fecha_fin=fecha_fin,
    )


@login_required(login_url='login')
def generar_inspecciones(request):
    from tpm.models import InspeccionDiaria

    denegado = _sin_permiso(request)
    if denegado:
        return denegado
    if request.method != 'POST':
        return redirect('lista_reportes')

    fecha_inicio = request.POST.get('fecha_inicio')
    fecha_fin = request.POST.get('fecha_fin')

    encabezados = ['Fecha', 'Máquina', 'Inspector', 'Limpieza', 'Temperatura', 'Guardas',
                   'Emergencia', 'Ruidos', 'Vibraciones', 'Ítems específicos (catálogo)',
                   'Resultado', 'Observaciones']

    qs = InspeccionDiaria.objects.select_related('maquina', 'inspector') \
                                 .prefetch_related('respuestas_checklist__item')
    if fecha_inicio:
        qs = qs.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        qs = qs.filter(fecha__lte=fecha_fin)

    ok_falla = lambda v: 'OK' if v else 'FALLA'

    filas = []
    for insp in qs:
        items_especificos = '; '.join(
            f"{r.item.nombre}: {'OK' if r.ok else 'FALLA'}" for r in insp.respuestas_checklist.all()
        ) or '—'
        filas.append([
            fmt_fecha(insp.fecha), insp.maquina.nombre, fmt_usuario(insp.inspector),
            ok_falla(insp.limpieza_area_ok), ok_falla(insp.temperatura_normal),
            ok_falla(insp.guardas_seguridad_ok), ok_falla(insp.boton_emergencia_ok),
            si_no(insp.ruidos_anormales), si_no(insp.vibraciones_anormales),
            items_especificos, 'Aprobada' if insp.aprobada else 'FALLIDA',
            fmt_texto(insp.observaciones),
        ])

    return generar_reporte_excel(
        request, tipo='TPM_INSPECCIONES', nombre_base='inspecciones',
        hojas=[('Inspecciones', encabezados, filas, 16)],
        fecha_inicio=fecha_inicio, fecha_fin=fecha_fin,
    )


@login_required(login_url='login')
def generar_oee(request):
    from maquinas.models import Maquina
    from tpm.models import RegistroOEE

    denegado = _sin_permiso(request)
    if denegado:
        return denegado
    if request.method != 'POST':
        return redirect('lista_reportes')

    anio = request.POST.get('anio')
    maquina_id = request.POST.get('maquina')

    encabezados = ['Período', 'Máquina', 'Código', 'Disponibilidad %',
                   'Rendimiento %', 'Calidad %', 'OEE %', 'Clasificación']

    registros = RegistroOEE.objects.select_related('maquina').all()
    partes_obs = []
    if anio:
        registros = registros.filter(anio=anio)
        partes_obs.append(f"Año {anio}")
    if maquina_id:
        registros = registros.filter(maquina_id=maquina_id)
        maquina = Maquina.objects.filter(pk=maquina_id).first()
        if maquina:
            partes_obs.append(f"Máquina {maquina.codigo}")
    registros = registros.order_by('anio', 'mes', 'maquina__nombre')

    filas = []
    for r in registros:
        oee = float(r.oee)
        filas.append([
            f"{r.mes:02d}/{r.anio}", r.maquina.nombre, r.maquina.codigo,
            float(r.disponibilidad), float(r.rendimiento), float(r.calidad), oee,
            'World class' if oee >= 85 else 'Aceptable' if oee >= 60 else 'Mejorar',
        ])

    return generar_reporte_excel(
        request, tipo='TPM_OEE', nombre_base='oee',
        hojas=[('OEE', encabezados, filas)],
        observaciones=', '.join(partes_obs) if partes_obs else 'Todos los registros',
    )


@login_required(login_url='login')
def generar_reservas(request):
    from reservas.models import Reserva

    denegado = _sin_permiso(request)
    if denegado:
        return denegado
    if request.method != 'POST':
        return redirect('lista_reportes')

    fecha_inicio = request.POST.get('fecha_inicio')
    fecha_fin = request.POST.get('fecha_fin')

    encabezados = ['#', 'Solicitante', 'Máquina', 'Código', 'Fecha',
                   'Hora inicio', 'Hora fin', 'Propósito', 'Estado',
                   'Autorizador', 'OT', 'T. planificado (min)', 'T. real (min)',
                   'T. paradas (min)', 'Unidades prod.', 'Unidades esp.']

    qs = Reserva.objects.select_related('usuario', 'maquina', 'autorizador', 'orden_trabajo')
    if fecha_inicio:
        qs = qs.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        qs = qs.filter(fecha__lte=fecha_fin)

    filas = []
    for r in qs:
        ot = getattr(r, 'orden_trabajo', None)
        filas.append([
            r.pk,
            fmt_usuario(r.usuario) if r.usuario else '— usuario eliminado —',
            r.maquina.nombre, r.maquina.codigo, fmt_fecha(r.fecha),
            r.hora_inicio.strftime('%H:%M'), r.hora_fin.strftime('%H:%M'),
            r.get_proposito_display(), r.get_estado_display(),
            fmt_usuario(r.autorizador),
            f'OT-{ot.pk:04d}' if ot else '—',
            float(ot.tiempo_planificado_min) if ot else '—',
            float(ot.tiempo_real_min) if ot and ot.tiempo_real_min else '—',
            float(ot.tiempo_parada_min) if ot else '—',
            ot.unidades_producidas if ot else '—',
            ot.unidades_esperadas if ot else '—',
        ])

    return generar_reporte_excel(
        request, tipo='RESERVAS', nombre_base='reservas',
        hojas=[('Reservas', encabezados, filas)],
        fecha_inicio=fecha_inicio, fecha_fin=fecha_fin,
    )


@login_required(login_url='login')
def generar_pareto(request):
    from reservas.models import RegistroParada
    from collections import defaultdict

    denegado = _sin_permiso(request)
    if denegado:
        return denegado
    if request.method != 'POST':
        return redirect('lista_reportes')

    fecha_inicio = request.POST.get('fecha_inicio')
    fecha_fin = request.POST.get('fecha_fin')

    encabezados = ['Código parada', 'Tipo', 'Categoría', 'Subsistema',
                   'Frecuencia', 'Duración total (min)', '% Frecuencia acumulada']

    qs = RegistroParada.objects.filter(activo=True).select_related('codigo_parada')
    if fecha_inicio:
        qs = qs.filter(orden_trabajo__reserva__fecha__gte=fecha_inicio)
    if fecha_fin:
        qs = qs.filter(orden_trabajo__reserva__fecha__lte=fecha_fin)

    # Agrupar por código de parada
    agrupado = defaultdict(lambda: {'frecuencia': 0, 'duracion': 0, 'obj': None})
    for p in qs:
        key = p.codigo_parada.codigo if p.codigo_parada else 'SIN_CÓDIGO'
        agrupado[key]['frecuencia'] += 1
        agrupado[key]['duracion'] += float(p.duracion_minutos or 0)
        agrupado[key]['obj'] = p.codigo_parada

    # Ordenar por frecuencia descendente
    ordenado = sorted(agrupado.items(), key=lambda x: x[1]['frecuencia'], reverse=True)
    total = sum(v['frecuencia'] for _, v in ordenado)
    acumulado = 0

    filas = []
    for codigo, datos in ordenado:
        acumulado += datos['frecuencia']
        pct = round((acumulado / total * 100), 1) if total > 0 else 0
        obj = datos['obj']
        filas.append([
            codigo,
            obj.get_tipo_display() if obj else '—',
            obj.get_categoria_display() if obj else '—',
            obj.subsistema if obj else '—',
            datos['frecuencia'], round(datos['duracion'], 2), pct,
        ])

    return generar_reporte_excel(
        request, tipo='TPM_PARETO', nombre_base='pareto_paradas',
        hojas=[('Pareto Paradas', encabezados, filas, 22)],
        fecha_inicio=fecha_inicio, fecha_fin=fecha_fin,
    )


@login_required(login_url='login')
def generar_ordenes_mantenimiento(request):
    from mantenimiento.models import OrdenMantenimiento

    denegado = _sin_permiso(request)
    if denegado:
        return denegado
    if request.method != 'POST':
        return redirect('lista_reportes')

    fecha_inicio = request.POST.get('fecha_inicio')
    fecha_fin = request.POST.get('fecha_fin')

    encabezados = ['Nº', 'Máquina', 'Código', 'Tipo', 'Estado', 'Prioridad',
                   'Origen', 'Referencia origen', 'Título', 'Responsables',
                   'Fecha programada', 'Fecha inicio', 'Fecha fin',
                   'T. estimado (h)', 'Costo', '¿Afecta seguridad?',
                   '¿Para producción?', 'Autorizado por', 'Creado por']

    qs = OrdenMantenimiento.objects.select_related(
        'maquina', 'responsable_1', 'responsable_2', 'responsable_3',
        'autorizado_por', 'creado_por', 'plan', 'incidente', 'inspeccion',
        'hallazgo', 'parada', 'bitacora_operario',
    )
    if fecha_inicio:
        qs = qs.filter(fecha_programada__gte=fecha_inicio)
    if fecha_fin:
        qs = qs.filter(fecha_programada__lte=fecha_fin)

    def referencia_origen(om):
        # Los FKs de origen son SET_NULL: puede haber origen declarado sin referencia
        ref = (om.plan or om.incidente or om.inspeccion or om.hallazgo
               or om.parada or om.bitacora_operario)
        return str(ref) if ref else '—'

    filas = []
    for om in qs:
        responsables = '; '.join(
            fmt_usuario(r) for r in (om.responsable_1, om.responsable_2, om.responsable_3) if r
        ) or '—'
        filas.append([
            om.numero(), om.maquina.nombre, om.maquina.codigo,
            om.get_tipo_display(), om.get_estado_display(), om.get_prioridad_display(),
            om.get_origen_display(), referencia_origen(om), om.titulo, responsables,
            fmt_fecha(om.fecha_programada), fmt_fecha_hora(om.fecha_inicio),
            fmt_fecha_hora(om.fecha_fin), fmt_num(om.tiempo_estimado_horas),
            float(om.costo), si_no(om.afecta_seguridad), si_no(om.para_produccion),
            fmt_usuario(om.autorizado_por), fmt_usuario(om.creado_por),
        ])

    return generar_reporte_excel(
        request, tipo='ORDENES_MANTENIMIENTO', nombre_base='ordenes_mantenimiento',
        hojas=[('Órdenes de mantenimiento', encabezados, filas, 20)],
        fecha_inicio=fecha_inicio, fecha_fin=fecha_fin,
    )


@login_required(login_url='login')
def generar_alertas(request):
    from tpm.models import Alerta

    denegado = _sin_permiso(request)
    if denegado:
        return denegado
    if request.method != 'POST':
        return redirect('lista_reportes')

    fecha_inicio = request.POST.get('fecha_inicio')
    fecha_fin = request.POST.get('fecha_fin')

    encabezados = ['ID', 'Tipo', 'Severidad', 'Máquina', 'Mensaje', 'Generada',
                   'Asignada a', 'Asignada en', 'Vista por', 'Vista en',
                   '¿Resuelta?', 'Resuelta por', 'Resuelta en',
                   'T. resolución (h)', 'Nota resolución']

    qs = Alerta.objects.select_related('maquina', 'asignado_a', 'vista_por', 'resuelta_por')
    if fecha_inicio:
        qs = qs.filter(generada_en__date__gte=fecha_inicio)
    if fecha_fin:
        qs = qs.filter(generada_en__date__lte=fecha_fin)

    filas = []
    for a in qs:
        horas_resolucion = (
            round((a.resuelta_en - a.generada_en).total_seconds() / 3600, 1)
            if a.resuelta_en else '—'
        )
        filas.append([
            a.pk, a.get_tipo_display(), a.get_severidad_display(),
            a.maquina.nombre if a.maquina else '—', a.mensaje,
            fmt_fecha_hora(a.generada_en),
            fmt_usuario(a.asignado_a), fmt_fecha_hora(a.asignado_en),
            fmt_usuario(a.vista_por), fmt_fecha_hora(a.vista_en),
            si_no(a.resuelta), fmt_usuario(a.resuelta_por),
            fmt_fecha_hora(a.resuelta_en), horas_resolucion,
            fmt_texto(a.nota_resolucion),
        ])

    return generar_reporte_excel(
        request, tipo='ALERTAS', nombre_base='alertas',
        hojas=[('Alertas', encabezados, filas)],
        fecha_inicio=fecha_inicio, fecha_fin=fecha_fin,
    )


@login_required(login_url='login')
def generar_certificaciones(request):
    from tpm.models import CertificacionUsuario

    denegado = _sin_permiso(request)
    if denegado:
        return denegado
    if request.method != 'POST':
        return redirect('lista_reportes')

    encabezados = ['Usuario', 'Máquina', 'Código', 'Otorgada por',
                   'Fecha otorgamiento', 'Fecha vencimiento', '¿Vigente?',
                   'Días para vencer', '¿Activa?', 'Observaciones']

    filas = [
        [fmt_usuario(c.usuario), c.maquina.nombre, c.maquina.codigo,
         fmt_usuario(c.otorgado_por), fmt_fecha(c.fecha_otorgamiento),
         fmt_fecha(c.fecha_vencimiento), si_no(c.vigente), c.dias_para_vencer,
         si_no(c.activo), fmt_texto(c.observaciones)]
        for c in CertificacionUsuario.objects.select_related('usuario', 'maquina', 'otorgado_por')
    ]

    return generar_reporte_excel(
        request, tipo='CERTIFICACIONES', nombre_base='certificaciones',
        hojas=[('Certificaciones', encabezados, filas)],
    )


@login_required(login_url='login')
def generar_incidentes(request):
    from tpm.models import Incidente

    denegado = _sin_permiso(request)
    if denegado:
        return denegado
    if request.method != 'POST':
        return redirect('lista_reportes')

    fecha_inicio = request.POST.get('fecha_inicio')
    fecha_fin = request.POST.get('fecha_fin')

    encabezados = ['Fecha ocurrencia', 'Máquina', 'Código', 'Reportado por',
                   'Tipo', 'Severidad', 'Descripción', 'Acción tomada',
                   '¿Requiere mantenimiento?', 'OMs generadas', '¿Activo?']

    qs = Incidente.objects.select_related('maquina', 'reportado_por') \
                          .prefetch_related('ordenes_generadas')
    if fecha_inicio:
        qs = qs.filter(fecha_ocurrencia__date__gte=fecha_inicio)
    if fecha_fin:
        qs = qs.filter(fecha_ocurrencia__date__lte=fecha_fin)

    filas = []
    for inc in qs:
        oms = '; '.join(om.numero() for om in inc.ordenes_generadas.all()) or '—'
        filas.append([
            fmt_fecha_hora(inc.fecha_ocurrencia), inc.maquina.nombre,
            inc.maquina.codigo, fmt_usuario(inc.reportado_por),
            inc.get_tipo_display(), inc.get_severidad_display(),
            inc.descripcion, fmt_texto(inc.accion_tomada),
            si_no(inc.requiere_mantenimiento), oms, si_no(inc.activo),
        ])

    return generar_reporte_excel(
        request, tipo='INCIDENTES', nombre_base='incidentes',
        hojas=[('Incidentes', encabezados, filas, 20)],
        fecha_inicio=fecha_inicio, fecha_fin=fecha_fin,
    )


@login_required(login_url='login')
def generar_consumos(request):
    from inventario.models import ConsumoMaterial

    denegado = _sin_permiso(request)
    if denegado:
        return denegado
    if request.method != 'POST':
        return redirect('lista_reportes')

    fecha_inicio = request.POST.get('fecha_inicio')
    fecha_fin = request.POST.get('fecha_fin')

    encabezados = ['Fecha', 'Material', 'Código', 'Unidad', 'Cantidad',
                   'OT', 'Registrado por', 'Observación']

    qs = ConsumoMaterial.objects.select_related('material', 'realizado_por', 'orden_trabajo')
    if fecha_inicio:
        qs = qs.filter(fecha__date__gte=fecha_inicio)
    if fecha_fin:
        qs = qs.filter(fecha__date__lte=fecha_fin)

    filas = [
        [fmt_fecha_hora(c.fecha), c.material.nombre, c.material.codigo,
         c.material.unidad_medida, float(c.cantidad),
         f'OT-{c.orden_trabajo.pk:04d}' if c.orden_trabajo else '—',
         fmt_usuario(c.realizado_por), fmt_texto(c.observacion)]
        for c in qs
    ]

    return generar_reporte_excel(
        request, tipo='CONSUMO_MATERIALES', nombre_base='consumos_materiales',
        hojas=[('Consumos', encabezados, filas)],
        fecha_inicio=fecha_inicio, fecha_fin=fecha_fin,
    )


@login_required(login_url='login')
def generar_piezas(request):
    from maquinas.models import Pieza, TransferenciaPieza, ReasignacionPieza

    denegado = _sin_permiso(request)
    if denegado:
        return denegado
    if request.method != 'POST':
        return redirect('lista_reportes')

    fecha_inicio = request.POST.get('fecha_inicio')
    fecha_fin = request.POST.get('fecha_fin')

    # Hoja 1 — Piezas (sin filtro de fechas: es el estado actual del despiece)
    enc_piezas = ['Máquina', 'Ruta completa', 'Nombre', 'Nombre inglés',
                  'Nº parte', 'Posición', '¿Es ensamble?', 'Stock repuestos',
                  'Stock mínimo', 'Estado stock']
    filas_piezas = []
    piezas = Pieza.objects.filter(activo=True) \
                          .select_related('maquina', 'ensamble') \
                          .order_by('maquina__nombre', 'ensamble__nombre', 'nombre')
    for p in piezas:
        filas_piezas.append([
            p.maquina.nombre, p.get_ruta_completa(), p.nombre,
            fmt_texto(p.nombre_en), fmt_texto(p.numero_parte),
            p.numero_posicion if p.numero_posicion is not None else '—',
            si_no(p.es_ensamble), p.stock_repuestos, p.stock_minimo_repuestos,
            '—' if p.es_ensamble else ('Stock bajo' if p.stock_bajo else 'OK'),
        ])

    # Hoja 2 — Transferencias (filtrable por fecha)
    enc_transf = ['Fecha', 'Pieza', 'Nº parte', 'Máquina origen',
                  'Máquina destino', 'Autorizado por', 'Motivo', 'Observaciones']
    qs_transf = TransferenciaPieza.objects.select_related(
        'pieza', 'maquina_origen', 'maquina_destino', 'autorizado_por')
    if fecha_inicio:
        qs_transf = qs_transf.filter(fecha__date__gte=fecha_inicio)
    if fecha_fin:
        qs_transf = qs_transf.filter(fecha__date__lte=fecha_fin)
    filas_transf = [
        [fmt_fecha_hora(t.fecha), t.pieza.nombre, fmt_texto(t.pieza.numero_parte),
         t.maquina_origen.nombre if t.maquina_origen else '—',
         t.maquina_destino.nombre if t.maquina_destino else '—',
         fmt_usuario(t.autorizado_por), fmt_texto(t.motivo), fmt_texto(t.observaciones)]
        for t in qs_transf
    ]

    # Hoja 3 — Reasignaciones entre ensambles (filtrable por fecha)
    enc_reasig = ['Fecha', 'Pieza', 'Ensamble anterior', 'Ensamble nuevo', 'Realizado por']
    qs_reasig = ReasignacionPieza.objects.select_related(
        'pieza', 'ensamble_anterior', 'ensamble_nuevo', 'realizado_por')
    if fecha_inicio:
        qs_reasig = qs_reasig.filter(fecha__date__gte=fecha_inicio)
    if fecha_fin:
        qs_reasig = qs_reasig.filter(fecha__date__lte=fecha_fin)
    filas_reasig = [
        [fmt_fecha_hora(r.fecha), r.pieza.nombre,
         r.ensamble_anterior.nombre if r.ensamble_anterior else '(suelta)',
         r.ensamble_nuevo.nombre if r.ensamble_nuevo else '(suelta)',
         fmt_usuario(r.realizado_por)]
        for r in qs_reasig
    ]

    return generar_reporte_excel(
        request, tipo='PIEZAS', nombre_base='piezas',
        hojas=[
            ('Piezas', enc_piezas, filas_piezas, 20),
            ('Transferencias', enc_transf, filas_transf, 20),
            ('Reasignaciones', enc_reasig, filas_reasig, 20),
        ],
        fecha_inicio=fecha_inicio, fecha_fin=fecha_fin,
    )


@login_required(login_url='login')
def generar_bitacoras(request):
    from mantenimiento.models import BitacoraMantenimiento
    from reservas.models import BitacoraOperario

    denegado = _sin_permiso(request)
    if denegado:
        return denegado
    if request.method != 'POST':
        return redirect('lista_reportes')

    fecha_inicio = request.POST.get('fecha_inicio')
    fecha_fin = request.POST.get('fecha_fin')

    # Hoja 1 — Bitácora de operarios (ligada a órdenes de trabajo)
    enc_oper = ['Fecha', 'OT', 'Máquina', 'Operario', 'Descripción',
                'Observaciones', '¿Requiere atención?', '¿Tiene foto?']
    qs_oper = BitacoraOperario.objects.select_related(
        'operario', 'orden_trabajo__reserva__maquina')
    if fecha_inicio:
        qs_oper = qs_oper.filter(fecha_registro__date__gte=fecha_inicio)
    if fecha_fin:
        qs_oper = qs_oper.filter(fecha_registro__date__lte=fecha_fin)
    filas_oper = [
        [fmt_fecha_hora(b.fecha_registro), f'OT-{b.orden_trabajo.pk:04d}',
         b.orden_trabajo.reserva.maquina.nombre, fmt_usuario(b.operario),
         b.descripcion_trabajo, fmt_texto(b.observaciones),
         si_no(b.requiere_atencion), si_no(bool(b.foto))]
        for b in qs_oper.order_by('-fecha_registro')
    ]

    # Hoja 2 — Bitácora de mantenimiento (ligada a máquinas / OMs)
    enc_mant = ['Fecha', 'Máquina', 'OM', 'Técnico', 'Tipo actividad',
                'Horas', 'Descripción', 'Repuestos utilizados', '¿Requiere atención?']
    qs_mant = BitacoraMantenimiento.objects.select_related('maquina', 'tecnico', 'orden')
    if fecha_inicio:
        qs_mant = qs_mant.filter(fecha_registro__date__gte=fecha_inicio)
    if fecha_fin:
        qs_mant = qs_mant.filter(fecha_registro__date__lte=fecha_fin)
    filas_mant = [
        [fmt_fecha_hora(b.fecha_registro), b.maquina.nombre,
         b.orden.numero() if b.orden else '—', fmt_usuario(b.tecnico),
         b.get_tipo_actividad_display() if b.tipo_actividad else '—',
         fmt_num(b.tiempo_horas), b.descripcion,
         fmt_texto(b.repuestos_utilizados), si_no(b.requiere_atencion)]
        for b in qs_mant
    ]

    return generar_reporte_excel(
        request, tipo='BITACORAS', nombre_base='bitacoras',
        hojas=[
            ('Bitácora operarios', enc_oper, filas_oper, 20),
            ('Bitácora mantenimiento', enc_mant, filas_mant, 20),
        ],
        fecha_inicio=fecha_inicio, fecha_fin=fecha_fin,
    )


@login_required(login_url='login')
def generar_resumen(request):
    from maquinas.models import Maquina, Pieza
    from mantenimiento.models import PlanMantenimiento
    from tpm.models import Alerta

    denegado = _sin_permiso(request)
    if denegado:
        return denegado
    if request.method != 'POST':
        return redirect('lista_reportes')

    hoy = timezone.now().date()

    pendientes = ReporteService.mantenimientos_pendientes()
    stock_bajo = ReporteService.materiales_stock_bajo()
    mas_usadas = ReporteService.maquinas_mas_utilizadas()
    tpm = ReporteService.indicadores_tpm()

    # Hoja 1 — KPIs generales
    enc_kpis = ['Indicador', 'Valor']
    filas_kpis = [['Total de máquinas', Maquina.objects.count()]]
    for estado, etiqueta in Maquina.ESTADOS:
        filas_kpis.append([f'Máquinas — {etiqueta}',
                           Maquina.objects.filter(estado=estado).count()])
    oms_vencidas = sum(1 for om in pendientes if om.fecha_programada < hoy)
    filas_kpis += [
        ['Órdenes de mantenimiento abiertas', len(pendientes)],
        ['Órdenes de mantenimiento vencidas', oms_vencidas],
        ['Planes de mantenimiento activos',
         PlanMantenimiento.objects.filter(activo=True).count()],
        ['Materiales en stock bajo', stock_bajo.count()],
        ['Piezas de repuesto en stock bajo',
         Pieza.objects.filter(activo=True, es_ensamble=False,
                              stock_repuestos__lte=F('stock_minimo_repuestos')).count()],
        [f"OEE promedio ({tpm['oee_periodo'] or 'sin registros'})",
         round(float(tpm['oee_promedio']), 2) if tpm['oee_promedio'] is not None else '—'],
    ]
    for severidad, etiqueta in Alerta.SEVERIDADES:
        filas_kpis.append([f'Alertas sin resolver — {etiqueta}',
                           tpm['alertas_activas'].get(severidad, 0)])
    filas_kpis += [
        ['Certificaciones por vencer (≤30 días)', tpm['certificaciones_por_vencer'].count()],
        ['Incidentes en los últimos 30 días', tpm['incidentes_30d']],
    ]

    # Hoja 2 — Máquinas más utilizadas
    enc_maquinas = ['Máquina', 'Código', 'Estado', 'Horas acumuladas']
    filas_maquinas = [
        [m.nombre, m.codigo, m.get_estado_display(), float(m.horas_acumuladas)]
        for m in mas_usadas
    ]

    # Hoja 3 — Materiales en stock bajo
    enc_stock = ['Código', 'Material', 'Stock actual', 'Stock mínimo', 'Unidad']
    filas_stock = [
        [m.codigo, m.nombre, float(m.stock_actual), float(m.stock_minimo), m.unidad_medida]
        for m in stock_bajo
    ]

    # Hoja 4 — Mantenimientos pendientes (OMs abiertas)
    enc_pend = ['Nº', 'Máquina', 'Título', 'Prioridad', 'Fecha programada',
                '¿Vencida?', 'Responsable']
    filas_pend = [
        [om.numero(), om.maquina.nombre, om.titulo, om.get_prioridad_display(),
         fmt_fecha(om.fecha_programada), si_no(om.fecha_programada < hoy),
         fmt_usuario(om.responsable_1)]
        for om in pendientes
    ]

    # Hoja 5 — Alertas activas
    enc_alertas = ['Tipo', 'Severidad', 'Máquina', 'Mensaje', 'Generada']
    filas_alertas = [
        [a.get_tipo_display(), a.get_severidad_display(),
         a.maquina.nombre if a.maquina else '—', a.mensaje,
         fmt_fecha_hora(a.generada_en)]
        for a in Alerta.objects.filter(resuelta=False).select_related('maquina')
    ]

    # Hoja 6 — Certificaciones por vencer
    enc_cert = ['Usuario', 'Máquina', 'Vence', 'Días restantes']
    filas_cert = [
        [fmt_usuario(c.usuario), c.maquina.nombre,
         fmt_fecha(c.fecha_vencimiento), c.dias_para_vencer]
        for c in tpm['certificaciones_por_vencer']
    ]

    return generar_reporte_excel(
        request, tipo='RESUMEN', nombre_base='resumen_ejecutivo',
        hojas=[
            ('KPIs', enc_kpis, filas_kpis, 34),
            ('Máquinas más utilizadas', enc_maquinas, filas_maquinas),
            ('Stock bajo', enc_stock, filas_stock),
            ('Mantenimientos pendientes', enc_pend, filas_pend, 20),
            ('Alertas activas', enc_alertas, filas_alertas, 22),
            ('Certificaciones por vencer', enc_cert, filas_cert, 20),
        ],
    )
