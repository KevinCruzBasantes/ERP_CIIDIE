import unicodedata

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Mantenimiento, PlanMantenimiento, OrdenMantenimiento, BitacoraMantenimiento
from .forms import MantenimientoForm, PlanMantenimientoForm, OrdenMantenimientoForm, BitacoraMantenimientoForm


def _normalizar_rol(nombre_rol):
    """Minúsculas y sin tildes, para que 'TECNICO' y 'Técnico' coincidan igual."""
    sin_tildes = unicodedata.normalize('NFKD', nombre_rol).encode('ascii', 'ignore').decode('ascii')
    return sin_tildes.lower()


def es_admin(user):
    if user.is_superuser:
        return True
    if user.rol:
        rol = _normalizar_rol(user.rol.nombre)
        return 'administrador' in rol or 'phd' in rol
    return False


def es_admin_o_tecnico(user):
    if user.is_superuser:
        return True
    if user.rol:
        rol = _normalizar_rol(user.rol.nombre)
        return any(r in rol for r in ['administrador', 'phd', 'tecnico', 'ingeniero'])
    return False


@login_required(login_url='login')
def lista_mantenimientos(request):
    hoy = timezone.now().date()
    todos = Mantenimiento.objects.select_related(
        'maquina', 'responsable', 'plan'
    ).filter(activo=True)

    context = {
        'mantenimientos': todos,
        'total': todos.count(),
        'programados': todos.filter(estado='PROGRAMADO').count(),
        'en_proceso': todos.filter(estado='EN_PROCESO').count(),
        'vencidos': todos.filter(
            estado__in=['PROGRAMADO', 'EN_PROCESO'],
            fecha_programada__lt=hoy
        ).count(),
        'finalizados': todos.filter(estado='FINALIZADO').count(),
        'es_admin_o_tecnico': es_admin_o_tecnico(request.user),
    }
    return render(request, 'mantenimiento/lista_mantenimientos.html', context)


@login_required(login_url='login')
def detalle_mantenimiento(request, pk):
    mantenimiento = get_object_or_404(
        Mantenimiento.objects.select_related('maquina', 'responsable', 'plan'),
        pk=pk, activo=True
    )
    context = {
        'm': mantenimiento,
        'es_admin_o_tecnico': es_admin_o_tecnico(request.user),
    }
    return render(request, 'mantenimiento/detalle_mantenimiento.html', context)


@login_required(login_url='login')
def crear_mantenimiento(request):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('lista_mantenimientos')

    if request.method == 'POST':
        form = MantenimientoForm(request.POST)
        if form.is_valid():
            mto = form.save()
            messages.success(request, f'Mantenimiento registrado correctamente.')
            return redirect('detalle_mantenimiento', pk=mto.pk)
    else:
        form = MantenimientoForm()

    context = {
        'form': form,
        'titulo': 'Nuevo mantenimiento',
        'accion': 'Registrar',
    }
    return render(request, 'mantenimiento/form_mantenimiento.html', context)


@login_required(login_url='login')
def editar_mantenimiento(request, pk):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('detalle_mantenimiento', pk=pk)

    mantenimiento = get_object_or_404(Mantenimiento, pk=pk, activo=True)

    if request.method == 'POST':
        form = MantenimientoForm(request.POST, instance=mantenimiento)
        if form.is_valid():
            form.save()
            messages.success(request, 'Mantenimiento actualizado correctamente.')
            return redirect('detalle_mantenimiento', pk=mantenimiento.pk)
    else:
        form = MantenimientoForm(instance=mantenimiento)

    context = {
        'form': form,
        'mantenimiento': mantenimiento,
        'titulo': f'Editar mantenimiento #{mantenimiento.pk}',
        'accion': 'Guardar cambios',
    }
    return render(request, 'mantenimiento/form_mantenimiento.html', context)


@login_required(login_url='login')
def eliminar_mantenimiento(request, pk):
    if not es_admin(request.user):
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('detalle_mantenimiento', pk=pk)

    mantenimiento = get_object_or_404(Mantenimiento, pk=pk, activo=True)

    if request.method == 'POST':
        mantenimiento.activo = False
        mantenimiento.save()
        messages.success(request, f'Mantenimiento #{mantenimiento.pk} eliminado correctamente.')
        return redirect('lista_mantenimientos')

    context = {'mantenimiento': mantenimiento}
    return render(request, 'mantenimiento/confirmar_eliminar_mantenimiento.html', context)

@login_required(login_url='login')
def cambiar_estado_mantenimiento(request, pk):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para esta acción.')
        return redirect('detalle_mantenimiento', pk=pk)
    mto = get_object_or_404(Mantenimiento, pk=pk, activo=True)
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado in ['PROGRAMADO', 'EN_PROCESO', 'FINALIZADO', 'CANCELADO']:
            mto.estado = nuevo_estado
            if nuevo_estado == 'EN_PROCESO' and not mto.fecha_inicio:
                mto.fecha_inicio = timezone.now()
            if nuevo_estado == 'FINALIZADO' and not mto.fecha_fin:
                mto.fecha_fin = timezone.now()
            mto.save()
            messages.success(request, f'Mantenimiento #{mto.pk} actualizado a {mto.get_estado_display()}.')
    return redirect('detalle_mantenimiento', pk=pk)


# ── PLANES DE MANTENIMIENTO ───────────────────────────────────────────────────

@login_required(login_url='login')
def lista_planes(request):
    planes = PlanMantenimiento.objects.select_related('maquina').filter(activo=True)
    eliminados = PlanMantenimiento.objects.select_related('maquina').filter(activo=False)
    context = {
        'planes':             planes,
        'total':              planes.count(),
        'autonomos':          planes.filter(tipo_tpm='P1_AUTONOMO').count(),
        'preventivos':        planes.filter(tipo_tpm='P2_PREVENTIVO').count(),
        'mejora':             planes.filter(tipo_tpm='P3_MEJORA').count(),
        'seguridad':          planes.filter(tipo_tpm='P7_SEGURIDAD').count(),
        'eliminados':         eliminados,
        'total_eliminados':   eliminados.count(),
        'es_admin_o_tecnico': es_admin_o_tecnico(request.user),
    }
    return render(request, 'mantenimiento/lista_planes.html', context)


@login_required(login_url='login')
def detalle_plan(request, pk):
    plan = get_object_or_404(
        PlanMantenimiento.objects.select_related('maquina'),
        pk=pk, activo=True
    )
    ejecuciones = plan.ejecuciones.select_related(
        'maquina', 'responsable'
    ).filter(activo=True).order_by('-fecha_programada')[:10]
    ordenes_generadas = plan.ordenes.filter(activo=True).order_by('-fecha_programada')[:10]
    context = {
        'plan':               plan,
        'ejecuciones':        ejecuciones,
        'total_ejecuciones':  plan.ejecuciones.filter(activo=True).count(),
        'ordenes_generadas':  ordenes_generadas,
        'es_admin_o_tecnico': es_admin_o_tecnico(request.user),
    }
    return render(request, 'mantenimiento/detalle_plan.html', context)


@login_required(login_url='login')
def crear_plan(request):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para crear planes de mantenimiento.')
        return redirect('lista_planes')

    if request.method == 'POST':
        form = PlanMantenimientoForm(request.POST)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.activo = True
            plan.save()
            messages.success(request, f'Plan "{plan.nombre_tarea}" creado correctamente.')
            return redirect('detalle_plan', pk=plan.pk)
    else:
        form = PlanMantenimientoForm()

    return render(request, 'mantenimiento/form_plan.html', {
        'form':   form,
        'titulo': 'Nuevo plan de mantenimiento',
        'accion': 'Crear plan',
    })


@login_required(login_url='login')
def editar_plan(request, pk):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para editar planes de mantenimiento.')
        return redirect('detalle_plan', pk=pk)

    plan = get_object_or_404(PlanMantenimiento, pk=pk, activo=True)

    if request.method == 'POST':
        form = PlanMantenimientoForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            messages.success(request, f'Plan "{plan.nombre_tarea}" actualizado correctamente.')
            return redirect('detalle_plan', pk=plan.pk)
    else:
        form = PlanMantenimientoForm(instance=plan)

    return render(request, 'mantenimiento/form_plan.html', {
        'form':   form,
        'plan':   plan,
        'titulo': f'Editar — {plan.nombre_tarea}',
        'accion': 'Guardar cambios',
    })


@login_required(login_url='login')
def eliminar_plan(request, pk):
    if not es_admin(request.user):
        messages.error(request, 'No tienes permisos para eliminar planes de mantenimiento.')
        return redirect('detalle_plan', pk=pk)

    plan = get_object_or_404(PlanMantenimiento, pk=pk, activo=True)

    if request.method == 'POST':
        plan.activo = False
        plan.save(update_fields=['activo'])
        messages.success(request, f'Plan "{plan.nombre_tarea}" eliminado correctamente.')
        return redirect('lista_planes')

    return render(request, 'mantenimiento/confirmar_eliminar_plan.html', {'plan': plan})


@login_required(login_url='login')
def restaurar_plan(request, pk):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para restaurar planes de mantenimiento.')
        return redirect('lista_planes')

    plan = get_object_or_404(PlanMantenimiento, pk=pk, activo=False)

    if request.method == 'POST':
        plan.activo = True
        plan.save(update_fields=['activo'])
        messages.success(request, f'Plan "{plan.nombre_tarea}" restaurado correctamente.')
        return redirect('detalle_plan', pk=plan.pk)

    return redirect('lista_planes')


@login_required(login_url='login')
def eliminar_plan_definitivo(request, pk):
    if not es_admin(request.user):
        messages.error(request, 'No tienes permisos para eliminar planes definitivamente.')
        return redirect('lista_planes')

    plan = get_object_or_404(PlanMantenimiento, pk=pk, activo=False)

    if request.method == 'POST':
        nombre = plan.nombre_tarea
        plan.delete()
        messages.success(request, f'Plan "{nombre}" eliminado definitivamente.')
        return redirect('lista_planes')

    return redirect('lista_planes')


# ── ÓRDENES DE MANTENIMIENTO ──────────────────────────────────────────────────

@login_required(login_url='login')
def lista_ordenes_mantenimiento(request):
    qs = OrdenMantenimiento.objects.select_related(
        'maquina', 'plan', 'responsable_1', 'creado_por'
    ).filter(activo=True).order_by('-fecha_programada')

    estado_f    = request.GET.get('estado', '')
    tipo_f      = request.GET.get('tipo', '')
    maquina_f   = request.GET.get('maquina', '')
    prioridad_f = request.GET.get('prioridad', '')

    if estado_f:
        qs = qs.filter(estado=estado_f)
    if tipo_f:
        qs = qs.filter(tipo=tipo_f)
    if maquina_f:
        qs = qs.filter(maquina__pk=maquina_f)
    if prioridad_f:
        qs = qs.filter(prioridad=prioridad_f)

    from maquinas.models import Maquina as MaquinaModel
    hoy = timezone.now().date()
    context = {
        'ordenes':         qs,
        'total':           qs.count(),
        'programadas':     qs.filter(estado='PROGRAMADA').count(),
        'en_proceso':      qs.filter(estado='EN_PROCESO').count(),
        'finalizadas':     qs.filter(estado='FINALIZADA').count(),
        'vencidas':        qs.filter(estado='PROGRAMADA', fecha_programada__lt=hoy).count(),
        'maquinas':        MaquinaModel.objects.exclude(estado='FUERA_SERVICIO').order_by('nombre'),
        'filtro_estado':   estado_f,
        'filtro_tipo':     tipo_f,
        'filtro_maquina':  maquina_f,
        'filtro_prioridad': prioridad_f,
        'hay_filtros':     any([estado_f, tipo_f, maquina_f, prioridad_f]),
        'es_admin_o_tecnico': es_admin_o_tecnico(request.user),
        'today':           hoy,
    }
    return render(request, 'mantenimiento/lista_ordenes_mantenimiento.html', context)


@login_required(login_url='login')
def detalle_orden_mantenimiento(request, pk):
    om = get_object_or_404(
        OrdenMantenimiento.objects.select_related(
            'maquina', 'plan', 'creado_por',
            'responsable_1', 'responsable_2', 'responsable_3',
            'autorizado_por'
        ),
        pk=pk, activo=True
    )
    entradas = om.entradas_bitacora.select_related('tecnico').order_by('-fecha_registro')
    form_bitacora = BitacoraMantenimientoForm()
    context = {
        'om':             om,
        'entradas':       entradas,
        'form_bitacora':  form_bitacora,
        'es_admin_o_tecnico': es_admin_o_tecnico(request.user),
        'es_admin':       es_admin(request.user),
    }
    return render(request, 'mantenimiento/detalle_orden_mantenimiento.html', context)


@login_required(login_url='login')
def crear_orden_mantenimiento(request):
    if not es_admin_o_tecnico(request.user):
        return redirect('lista_ordenes_mantenimiento')

    from tpm.models import Incidente as IncidenteModel

    incidente_obj = None
    incidente_pk  = request.GET.get('incidente') or request.POST.get('_incidente_pk')
    if incidente_pk:
        try:
            incidente_obj = IncidenteModel.objects.select_related('maquina').get(pk=incidente_pk)
        except IncidenteModel.DoesNotExist:
            pass

    if request.method == 'POST':
        form = OrdenMantenimientoForm(request.POST)
        if form.is_valid():
            om = form.save(commit=False)
            om.creado_por = request.user
            if incidente_obj:
                om.incidente = incidente_obj
                om.tipo = 'CORRECTIVO'
                om.origen = 'INCIDENTE'
            elif om.plan_id:
                om.origen = 'PLAN'
            om.save()
            return redirect('detalle_orden_mantenimiento', pk=om.pk)
    else:
        initial = {}
        if request.GET.get('maquina'):
            initial['maquina'] = request.GET['maquina']
        if request.GET.get('plan'):
            initial['plan'] = request.GET['plan']
        # Pre-llenar desde incidente
        if incidente_obj:
            sev_to_prior = {'BAJA': 'BAJA', 'MEDIA': 'MEDIA', 'ALTA': 'ALTA', 'CRITICA': 'CRITICA'}
            initial.update({
                'maquina':          incidente_obj.maquina.pk,
                'tipo':             'CORRECTIVO',
                'prioridad':        sev_to_prior.get(incidente_obj.severidad, 'ALTA'),
                'titulo':           f"Correctivo: {incidente_obj.get_tipo_display()} — {incidente_obj.maquina.nombre}",
                'descripcion_tarea': incidente_obj.descripcion,
            })
        form = OrdenMantenimientoForm(initial=initial)

    return render(request, 'mantenimiento/form_orden_mantenimiento.html', {
        'form':         form,
        'titulo':       'Nueva orden de mantenimiento',
        'accion':       'Crear orden',
        'incidente_obj': incidente_obj,
    })


@login_required(login_url='login')
def editar_orden_mantenimiento(request, pk):
    if not es_admin_o_tecnico(request.user):
        return redirect('detalle_orden_mantenimiento', pk=pk)

    om = get_object_or_404(OrdenMantenimiento, pk=pk, activo=True)
    if om.estado == 'FINALIZADA':
        return redirect('detalle_orden_mantenimiento', pk=pk)

    if request.method == 'POST':
        form = OrdenMantenimientoForm(request.POST, instance=om)
        if form.is_valid():
            form.save()
            return redirect('detalle_orden_mantenimiento', pk=om.pk)
    else:
        form = OrdenMantenimientoForm(instance=om)

    return render(request, 'mantenimiento/form_orden_mantenimiento.html', {
        'form':   form,
        'om':     om,
        'titulo': f'Editar {om.numero()}',
        'accion': 'Guardar cambios',
    })


@login_required(login_url='login')
def cambiar_estado_om(request, pk):
    if not es_admin_o_tecnico(request.user):
        return redirect('detalle_orden_mantenimiento', pk=pk)

    om = get_object_or_404(OrdenMantenimiento, pk=pk, activo=True)
    if request.method == 'POST':
        nuevo = request.POST.get('estado')
        validos = [c[0] for c in OrdenMantenimiento.ESTADOS]
        if nuevo in validos:
            om.estado = nuevo
            if nuevo == 'EN_PROCESO' and not om.fecha_inicio:
                om.fecha_inicio = timezone.now()
            if nuevo == 'FINALIZADA' and not om.fecha_fin:
                om.fecha_fin = timezone.now()
                if es_admin(request.user) and not om.autorizado_por:
                    om.autorizado_por    = request.user
                    om.fecha_autorizacion = timezone.now()
            om.save()
    return redirect('detalle_orden_mantenimiento', pk=pk)


@login_required(login_url='login')
def eliminar_orden_mantenimiento(request, pk):
    if not es_admin(request.user):
        return redirect('detalle_orden_mantenimiento', pk=pk)

    om = get_object_or_404(OrdenMantenimiento, pk=pk, activo=True)
    if request.method == 'POST':
        om.activo = False
        om.save(update_fields=['activo'])
        return redirect('lista_ordenes_mantenimiento')

    return render(request, 'mantenimiento/confirmar_eliminar_om.html', {'om': om})


# ── BITÁCORA DE MANTENIMIENTO ─────────────────────────────────────────────────

@login_required(login_url='login')
def agregar_entrada_bitacora(request, om_pk):
    om = get_object_or_404(OrdenMantenimiento, pk=om_pk, activo=True)
    if request.method == 'POST':
        form = BitacoraMantenimientoForm(request.POST, request.FILES)
        if form.is_valid():
            entrada = form.save(commit=False)
            entrada.maquina = om.maquina
            entrada.orden   = om
            entrada.tecnico = request.user
            entrada.save()
    return redirect('detalle_orden_mantenimiento', pk=om_pk)


@login_required(login_url='login')
def bitacora_maquina(request, maquina_pk):
    from maquinas.models import Maquina as MaquinaModel
    maquina = get_object_or_404(MaquinaModel, pk=maquina_pk)
    entradas = BitacoraMantenimiento.objects.select_related(
        'orden', 'tecnico'
    ).filter(maquina=maquina).order_by('-fecha_registro')
    context = {
        'maquina':  maquina,
        'entradas': entradas,
        'total':    entradas.count(),
        'es_admin_o_tecnico': es_admin_o_tecnico(request.user),
    }
    return render(request, 'mantenimiento/bitacora_maquina.html', context)