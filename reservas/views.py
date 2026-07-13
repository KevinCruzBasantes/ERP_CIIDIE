from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation
from usuarios.permisos import es_admin, es_admin_o_tecnico, es_estudiante, es_operador
from usuarios.models import Usuario
from .models import Reserva, OrdenTrabajo, RegistroParada, BitacoraOperario
from .forms import (ReservaForm, OrdenTrabajoForm, CerrarOrdenForm,
                    RegistroParadaForm, BitacoraForm)
from inventario.models import Material, ConsumoMaterial


# ── RESERVAS ─────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def lista_reservas(request):
    reservas = Reserva.objects.select_related('usuario', 'maquina', 'autorizador').all()
    if es_estudiante(request.user):
        reservas = reservas.filter(usuario=request.user)
    elif es_operador(request.user):
        # El operador ve las reservas que solicitó y las que le fueron asignadas.
        reservas = reservas.filter(Q(usuario=request.user) | Q(operador=request.user))
    context = {
        'reservas':           reservas,
        'total':              reservas.count(),
        'pendientes':         reservas.filter(estado='PENDIENTE').count(),
        'aprobadas':          reservas.filter(estado='APROBADA').count(),
        'en_uso':             reservas.filter(estado='EN_USO').count(),
        'completadas':        reservas.filter(estado='COMPLETADA').count(),
        'es_admin_o_tecnico': es_admin_o_tecnico(request.user),
    }
    return render(request, 'reservas/lista_reservas.html', context)


@login_required(login_url='login')
def crear_reserva(request):
    solicitante_es_estudiante = es_estudiante(request.user)
    if request.method == 'POST':
        form = ReservaForm(request.POST, solicitante_es_estudiante=solicitante_es_estudiante)
        if form.is_valid():
            reserva = form.save(commit=False)
            reserva.usuario = request.user
            reserva.estado  = 'PENDIENTE'
            try:
                reserva.save()
                messages.success(request, f'Reserva solicitada para {reserva.maquina.nombre} el {reserva.fecha.strftime("%d/%m/%Y")}. Pendiente de aprobación.')
                return redirect('detalle_reserva', pk=reserva.pk)
            except ValidationError as e:
                messages.error(request, f'No se pudo guardar la reserva: {"; ".join(e.messages)}')
    else:
        form = ReservaForm(solicitante_es_estudiante=solicitante_es_estudiante)
    return render(request, 'reservas/form_reserva.html', {
        'form':   form,
        'titulo': 'Nueva reserva',
        'accion': 'Solicitar reserva',
    })


@login_required(login_url='login')
def operadores_certificados(request):
    """JSON con los operadores activos y certificados para una máquina y,
    si se recibe fecha/horario, además disponibles según su horario declarado
    (un operador sin bloques de horario se asume disponible siempre)."""
    maquina_id = request.GET.get('maquina')
    if not maquina_id:
        return JsonResponse({'operadores': []})
    try:
        operadores = list(Usuario.objects.filter(
            rol__nombre__iexact='OPERADOR',
            estado='ACTIVO',
            certificaciones__maquina_id=int(maquina_id),
            certificaciones__activo=True,
            certificaciones__fecha_vencimiento__gte=date.today(),
        ).distinct().order_by('first_name', 'last_name'))
    except (ValueError, TypeError):
        return JsonResponse({'operadores': []})

    fecha_str       = request.GET.get('fecha')
    hora_inicio_str = request.GET.get('hora_inicio')
    hora_fin_str    = request.GET.get('hora_fin')
    if fecha_str:
        try:
            dia_semana   = datetime.strptime(fecha_str, '%Y-%m-%d').date().weekday()
            hora_ini_obj = datetime.strptime(hora_inicio_str, '%H:%M').time() if hora_inicio_str else None
            hora_fin_obj = datetime.strptime(hora_fin_str, '%H:%M').time() if hora_fin_str else None
            disponibles = []
            for o in operadores:
                bloques = o.disponibilidad.filter(activo=True)
                if not bloques.exists():
                    disponibles.append(o)  # sin horario declarado = siempre disponible
                    continue
                bloques_del_dia = bloques.filter(dia_semana=dia_semana)
                if not bloques_del_dia.exists():
                    continue  # no trabaja ese día de la semana
                if hora_ini_obj and hora_fin_obj:
                    if bloques_del_dia.filter(hora_inicio__lte=hora_ini_obj, hora_fin__gte=hora_fin_obj).exists():
                        disponibles.append(o)
                else:
                    disponibles.append(o)  # aún no se eligió horario; ya sabemos que trabaja ese día
            operadores = disponibles
        except ValueError:
            pass

    return JsonResponse({'operadores': [
        {'id': o.pk, 'nombre': o.get_full_name() or o.username} for o in operadores
    ]})


@login_required(login_url='login')
def disponibilidad_operadores_maquina(request):
    """JSON con el resumen semanal de disponibilidad de los operadores
    certificados para una máquina, para que el estudiante vea de una vez
    qué días tienen cobertura en vez de ir probando fechas al azar."""
    maquina_id = request.GET.get('maquina')
    if not maquina_id:
        return JsonResponse({'siempre_disponibles': [], 'por_dia': {}})
    try:
        operadores = Usuario.objects.filter(
            rol__nombre__iexact='OPERADOR',
            estado='ACTIVO',
            certificaciones__maquina_id=int(maquina_id),
            certificaciones__activo=True,
            certificaciones__fecha_vencimiento__gte=date.today(),
        ).distinct().prefetch_related('disponibilidad')
    except (ValueError, TypeError):
        return JsonResponse({'siempre_disponibles': [], 'por_dia': {}})

    siempre_disponibles = []
    por_dia = {str(d): [] for d in range(7)}
    for o in operadores:
        nombre  = o.get_full_name() or o.username
        bloques = [b for b in o.disponibilidad.all() if b.activo]
        if not bloques:
            siempre_disponibles.append(nombre)
            continue
        for b in bloques:
            por_dia[str(b.dia_semana)].append({
                'operador':    nombre,
                'hora_inicio': b.hora_inicio.strftime('%H:%M'),
                'hora_fin':    b.hora_fin.strftime('%H:%M'),
            })

    return JsonResponse({'siempre_disponibles': siempre_disponibles, 'por_dia': por_dia})


@login_required(login_url='login')
def horarios_ocupados(request):
    """JSON con las reservas activas de una maquina en una fecha, para mostrar
    en el formulario de crear/editar reserva y evitar horarios ya tomados."""
    maquina_id = request.GET.get('maquina')
    fecha      = request.GET.get('fecha')
    excluir_pk = request.GET.get('excluir')

    if not maquina_id or not fecha:
        return JsonResponse({'reservas': []})

    try:
        qs = Reserva.objects.filter(
            maquina_id=int(maquina_id),
            fecha=fecha,
            estado__in=('PENDIENTE', 'APROBADA', 'EN_USO'),
        ).select_related('usuario').order_by('hora_inicio')
        if excluir_pk:
            qs = qs.exclude(pk=int(excluir_pk))
        list(qs)  # forzar evaluacion aqui para que un valor invalido caiga en el except
    except (ValueError, ValidationError):
        return JsonResponse({'reservas': []})

    reservas = [
        {
            'hora_inicio': r.hora_inicio.strftime('%H:%M'),
            'hora_fin':    r.hora_fin.strftime('%H:%M'),
            'estado':      r.get_estado_display(),
            'usuario':     (r.usuario.get_full_name() or r.usuario.username) if r.usuario else 'Usuario eliminado',
        }
        for r in qs
    ]
    return JsonResponse({'reservas': reservas})


@login_required(login_url='login')
def detalle_reserva(request, pk):
    reserva = get_object_or_404(
        Reserva.objects.select_related('usuario', 'maquina', 'autorizador'), pk=pk)
    if es_estudiante(request.user) and reserva.usuario_id != request.user.pk:
        messages.error(request, 'No tienes acceso a esa reserva.')
        return redirect('lista_reservas')
    orden = getattr(reserva, 'orden_trabajo', None)
    es_propia          = reserva.usuario == request.user
    es_operador_asignado = reserva.operador_id == request.user.pk
    context = {
        'reserva':            reserva,
        'orden':              orden,
        'es_admin_o_tecnico': es_admin_o_tecnico(request.user),
        'es_admin':           es_admin(request.user),
        'es_propia':          es_propia,
        # Quién puede crear/ver la OT desde el detalle de la reserva:
        # el solicitante, el operador asignado o el staff.
        'puede_gestionar_orden': es_propia or es_operador_asignado or es_admin_o_tecnico(request.user),
    }
    return render(request, 'reservas/detalle_reserva.html', context)


@login_required(login_url='login')
def cambiar_estado_reserva(request, pk):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para esta acción.')
        return redirect('detalle_reserva', pk=pk)
    reserva = get_object_or_404(Reserva, pk=pk)
    if reserva.usuario_id == request.user.pk:
        messages.error(
            request,
            'No puedes aprobar o rechazar tu propia reserva. Otra persona calificada debe hacerlo.'
        )
        return redirect('detalle_reserva', pk=pk)
    nuevo_estado = request.POST.get('estado')
    estados_validos = ['PENDIENTE', 'APROBADA', 'EN_USO', 'COMPLETADA', 'CANCELADA']
    if request.method == 'POST' and nuevo_estado in estados_validos:
        reserva.estado = nuevo_estado
        if nuevo_estado == 'APROBADA':
            reserva.autorizador = request.user
        try:
            reserva.save()
            messages.success(request, f'Reserva #{reserva.pk} actualizada a {reserva.get_estado_display()}.')
            # Aprobar/rechazar es responsabilidad de quien autoriza; crear la OT y
            # llenar la bitácora le corresponde al dueño de la reserva (botón
            # "Crear OT" en su propio detalle), no a quien la aprobó.
        except ValidationError as e:
            messages.error(request, f'No se pudo actualizar la reserva: {"; ".join(e.messages)}')
    elif request.method == 'POST':
        messages.error(request, 'Estado inválido.')
    return redirect('detalle_reserva', pk=pk)


@login_required(login_url='login')
def editar_reserva(request, pk):
    reserva = get_object_or_404(Reserva, pk=pk)

    puede = reserva.usuario == request.user or es_admin_o_tecnico(request.user)
    if not puede:
        messages.error(request, 'No tienes permisos para editar esta reserva.')
        return redirect('detalle_reserva', pk=pk)

    if reserva.estado != 'PENDIENTE':
        messages.error(request, 'Solo se pueden editar reservas en estado Pendiente.')
        return redirect('detalle_reserva', pk=pk)

    solicitante_es_estudiante = es_estudiante(reserva.usuario) if reserva.usuario else False
    if request.method == 'POST':
        form = ReservaForm(request.POST, instance=reserva, solicitante_es_estudiante=solicitante_es_estudiante)
        form.fields['fecha'].widget.attrs.pop('min', None)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f'Reserva #{reserva.pk} actualizada correctamente.')
                return redirect('detalle_reserva', pk=reserva.pk)
            except ValidationError as e:
                messages.error(request, f'No se pudo guardar: {"; ".join(e.messages)}')
    else:
        form = ReservaForm(instance=reserva, solicitante_es_estudiante=solicitante_es_estudiante)
        form.fields['fecha'].widget.attrs.pop('min', None)

    return render(request, 'reservas/form_reserva.html', {
        'form':    form,
        'reserva': reserva,
        'titulo':  f'Editar reserva #{reserva.pk}',
        'accion':  'Guardar cambios',
    })


@login_required(login_url='login')
def cancelar_reserva(request, pk):
    reserva = get_object_or_404(Reserva, pk=pk)
    puede  = (reserva.usuario == request.user or es_admin_o_tecnico(request.user))
    if not puede:
        messages.error(request, 'Solo puedes cancelar tus propias reservas.')
        return redirect('detalle_reserva', pk=pk)
    if reserva.estado in ('COMPLETADA', 'CANCELADA'):
        messages.error(request, 'Esta reserva ya no puede cancelarse.')
        return redirect('detalle_reserva', pk=pk)
    if request.method == 'POST':
        reserva.estado = 'CANCELADA'
        reserva.save()
        messages.success(request, f'Reserva #{reserva.pk} cancelada.')
        return redirect('lista_reservas')
    return render(request, 'reservas/confirmar_cancelar_reserva.html', {'reserva': reserva})


# ── ÓRDENES DE TRABAJO ────────────────────────────────────────────────────────

@login_required(login_url='login')
def lista_ordenes(request):
    ordenes = OrdenTrabajo.objects.select_related(
        'reserva__usuario', 'reserva__maquina').filter(activo=True)
    if es_estudiante(request.user):
        ordenes = ordenes.filter(reserva__usuario=request.user)
    elif es_operador(request.user):
        # El operador ve las órdenes de las reservas que solicitó o le asignaron.
        ordenes = ordenes.filter(
            Q(reserva__usuario=request.user) | Q(reserva__operador=request.user))
    context = {
        'ordenes':            ordenes,
        'total':              ordenes.count(),
        'abiertas':           ordenes.filter(estado='ABIERTA').count(),
        'en_proceso':         ordenes.filter(estado='EN_PROCESO').count(),
        'finalizadas':        ordenes.filter(estado='FINALIZADA').count(),
        'es_admin_o_tecnico': es_admin_o_tecnico(request.user),
    }
    return render(request, 'reservas/lista_ordenes.html', context)


@login_required(login_url='login')
def crear_orden(request, reserva_pk):
    reserva = get_object_or_404(Reserva, pk=reserva_pk, estado='APROBADA')
    puede = (
        es_admin_o_tecnico(request.user)
        or reserva.usuario_id == request.user.pk       # solicitante
        or reserva.operador_id == request.user.pk       # operador asignado
    )
    if not puede:
        messages.error(request, 'No tienes acceso a esa reserva.')
        return redirect('lista_reservas')
    if hasattr(reserva, 'orden_trabajo'):
        messages.warning(request, 'Esta reserva ya tiene una orden de trabajo.')
        return redirect('detalle_orden', pk=reserva.orden_trabajo.pk)
    if request.method == 'POST':
        form = OrdenTrabajoForm(request.POST)
        if form.is_valid():
            orden          = form.save(commit=False)
            orden.reserva  = reserva
            orden.estado   = 'ABIERTA'
            orden.save()
            reserva.estado = 'EN_USO'
            reserva.save()
            messages.success(request, f'Orden OT-{orden.pk:04d} creada y reserva marcada En uso.')
            return redirect('detalle_orden', pk=orden.pk)
    else:
        ini     = datetime.combine(date.today(), reserva.hora_inicio)
        fin     = datetime.combine(date.today(), reserva.hora_fin)
        minutos = int((fin - ini).seconds / 60)
        form    = OrdenTrabajoForm(initial={'tiempo_planificado_min': minutos})
    return render(request, 'reservas/form_orden.html', {
        'form':    form,
        'reserva': reserva,
        'titulo':  f'Nueva OT — {reserva.maquina.nombre}',
        'accion':  'Crear orden de trabajo',
    })


def _es_participante_orden(user, orden):
    """Quién puede VER una OT: el staff (admin/técnico), el solicitante dueño
    de la reserva, o el operador asignado a ella."""
    if es_admin_o_tecnico(user):
        return True
    reserva = orden.reserva
    return reserva.usuario_id == user.pk or reserva.operador_id == user.pk


def _puede_registrar_en_orden(user, orden):
    """Quién puede ESCRIBIR en una OT (bitácora/paradas/consumos/cierre): igual
    que participante pero excluyendo al estudiante, que siempre delega en un
    operador y es de solo lectura sobre la OT."""
    return _es_participante_orden(user, orden) and not es_estudiante(user)


def _contexto_detalle_orden(request, orden, parada_form=None):
    orden = get_object_or_404(
        OrdenTrabajo.objects.select_related(
            'reserva__usuario', 'reserva__maquina'
        ).prefetch_related('paradas__codigo_parada', 'entradas_bitacora__operario'),
        pk=orden.pk, activo=True
    )

    proxima_reserva   = None
    minutos_restantes = None
    if orden.estado != 'FINALIZADA':
        reserva  = orden.reserva
        ahora_dt = datetime.now()
        limite_dt = datetime.combine(date.today(), reserva.hora_fin) - timedelta(minutes=15)
        if date.today() == reserva.fecha and ahora_dt >= limite_dt:
            proxima_reserva = Reserva.objects.filter(
                maquina=reserva.maquina,
                fecha=reserva.fecha,
                hora_inicio__gte=reserva.hora_fin,
                estado__in=('PENDIENTE', 'APROBADA', 'EN_USO'),
            ).select_related('usuario').order_by('hora_inicio').first()
            if proxima_reserva:
                fin_dt = datetime.combine(date.today(), reserva.hora_fin)
                minutos_restantes = max(0, int((fin_dt - ahora_dt).total_seconds() / 60))

    return {
        'orden':              orden,
        'paradas':            orden.paradas.filter(activo=True),
        'bitacora':           orden.entradas_bitacora.all(),
        'consumos':           orden.consumos_material.select_related('material').all(),
        'parada_form':        parada_form or RegistroParadaForm(maquina=orden.reserva.maquina, reserva=orden.reserva),
        'bitacora_form':      BitacoraForm(),
        'materiales':         Material.objects.filter(activo=True).order_by('nombre'),
        'cerrar_form':        CerrarOrdenForm(instance=orden),
        'es_admin_o_tecnico': es_admin_o_tecnico(request.user),
        # Puede registrar trabajo (bitácora/paradas/consumos) y cerrar la OT:
        # el operador asignado, el staff, o un solicitante de rol superior que
        # opere su propia reserva. El estudiante queda excluido: siempre delega
        # en un operador y es de solo lectura sobre la OT (no escribe en la
        # bitácora del operario ni registra nada).
        'puede_editar_orden': (
            orden.estado != 'FINALIZADA'
            and _puede_registrar_en_orden(request.user, orden)
        ),
        'proxima_reserva':    proxima_reserva,
        'minutos_restantes':  minutos_restantes,
    }


@login_required(login_url='login')
def detalle_orden(request, pk):
    orden = get_object_or_404(OrdenTrabajo, pk=pk, activo=True)
    if not _es_participante_orden(request.user, orden):
        messages.error(request, 'No tienes acceso a esa orden de trabajo.')
        return redirect('lista_ordenes')
    return render(request, 'reservas/detalle_orden.html', _contexto_detalle_orden(request, orden))


def _advertir_sobretiempo(request, orden, tiempo_real_min):
    if not tiempo_real_min:
        return
    reserva = orden.reserva
    hora_fin_real = (
        datetime.combine(reserva.fecha, reserva.hora_inicio)
        + timedelta(minutes=float(tiempo_real_min))
    )
    hora_fin_reservada = datetime.combine(reserva.fecha, reserva.hora_fin)
    if hora_fin_real <= hora_fin_reservada:
        return
    conflictos = Reserva.objects.filter(
        maquina=reserva.maquina,
        fecha=reserva.fecha,
        hora_inicio__gte=reserva.hora_fin,
        hora_inicio__lt=hora_fin_real.time(),
        estado__in=('PENDIENTE', 'APROBADA', 'EN_USO'),
    ).select_related('usuario').order_by('hora_inicio')
    for conflicto in conflictos:
        nombre = (
            conflicto.usuario.get_full_name() or conflicto.usuario.username
            if conflicto.usuario else '(usuario eliminado)'
        )
        messages.warning(
            request,
            f'Sobretiempo: el tiempo real ({tiempo_real_min} min) supera el horario de esta reserva '
            f'({reserva.hora_fin.strftime("%H:%M")}). Afecta la reserva de {nombre}, '
            f'que comienza a las {conflicto.hora_inicio.strftime("%H:%M")}.'
        )


@login_required(login_url='login')
def cerrar_orden(request, pk):
    orden = get_object_or_404(OrdenTrabajo, pk=pk, activo=True)
    if not _puede_registrar_en_orden(request.user, orden):
        messages.error(request, 'No tienes permiso para modificar esta orden de trabajo.')
        return redirect('detalle_orden', pk=pk)
    if orden.estado == 'FINALIZADA':
        messages.error(request, 'Esta orden ya está finalizada.')
        return redirect('detalle_orden', pk=pk)
    if request.method == 'POST':
        form = CerrarOrdenForm(request.POST, instance=orden)
        if form.is_valid():
            ot        = form.save(commit=False)
            ot.estado = 'FINALIZADA'
            ot.save()
            orden.reserva.estado = 'COMPLETADA'
            orden.reserva.save()
            if ot.tiempo_real_min:
                from django.db.models import F
                from decimal import Decimal
                from maquinas.models import Maquina as MaquinaModel
                MaquinaModel.objects.filter(pk=orden.reserva.maquina_id).update(
                    horas_acumuladas=F('horas_acumuladas') + Decimal(str(ot.tiempo_real_min)) / 60
                )
            messages.success(request, f'OT-{orden.pk:04d} finalizada correctamente.')
            _advertir_sobretiempo(request, orden, ot.tiempo_real_min)
        else:
            messages.error(request, 'Revisa los datos del cierre.')
    return redirect('detalle_orden', pk=pk)


@login_required(login_url='login')
def agregar_parada(request, orden_pk):
    orden = get_object_or_404(OrdenTrabajo, pk=orden_pk, activo=True)
    if not _puede_registrar_en_orden(request.user, orden):
        messages.error(request, 'No tienes permiso para modificar esta orden de trabajo.')
        return redirect('detalle_orden', pk=orden_pk)
    if request.method == 'POST':
        form = RegistroParadaForm(request.POST, maquina=orden.reserva.maquina, reserva=orden.reserva)
        if form.is_valid():
            parada              = form.save(commit=False)
            parada.orden_trabajo = orden
            parada.save()
            messages.success(request, 'Parada registrada.')
            return redirect('detalle_orden', pk=orden_pk)
        messages.error(request, 'No se pudo registrar la parada. Revisa los campos marcados.')
        return render(request, 'reservas/detalle_orden.html', _contexto_detalle_orden(request, orden, parada_form=form))
    return redirect('detalle_orden', pk=orden_pk)


@login_required(login_url='login')
def agregar_bitacora(request, orden_pk):
    orden = get_object_or_404(OrdenTrabajo, pk=orden_pk, activo=True)
    if not _puede_registrar_en_orden(request.user, orden):
        messages.error(request, 'No tienes permiso para modificar esta orden de trabajo.')
        return redirect('detalle_orden', pk=orden_pk)
    if request.method == 'POST':
        form = BitacoraForm(request.POST)
        if form.is_valid():
            entrada              = form.save(commit=False)
            entrada.orden_trabajo = orden
            entrada.operario     = request.user
            entrada.save()
            messages.success(request, 'Entrada de bitácora registrada.')
        else:
            detalle = '; '.join(
                '; '.join(errores) for errores in form.errors.values()
            )
            messages.error(request, f'Error en bitácora: {detalle}')
    return redirect('detalle_orden', pk=orden_pk)


@login_required(login_url='login')
def registrar_consumo(request, orden_pk):
    orden = get_object_or_404(OrdenTrabajo, pk=orden_pk, activo=True)
    if not _puede_registrar_en_orden(request.user, orden):
        messages.error(request, 'No tienes permiso para modificar esta orden de trabajo.')
        return redirect('detalle_orden', pk=orden_pk)
    if request.method == 'POST':
        material_id = request.POST.get('material_id')
        observacion = request.POST.get('observacion', '')
        try:
            material = Material.objects.get(pk=material_id, activo=True)
            # Decimal, no float: stock_actual es DecimalField y Decimal -= float
            # lanza TypeError (el consumo jamás se registraba).
            try:
                cantidad = Decimal(request.POST.get('cantidad', '') or '0')
            except InvalidOperation:
                raise ValueError('Cantidad inválida.')
            if cantidad <= 0:
                raise ValueError('La cantidad debe ser mayor que 0.')
            if material.stock_actual < cantidad:
                messages.error(request, f'Stock insuficiente. Disponible: {material.stock_actual} {material.unidad_medida}')
            else:
                ConsumoMaterial.objects.create(
                    material=material,
                    orden_trabajo=orden,
                    realizado_por=request.user,
                    cantidad=cantidad,
                    observacion=observacion,
                )
                messages.success(request, f'Consumo de {cantidad} {material.unidad_medida} de "{material.nombre}" registrado.')
        except Material.DoesNotExist:
            messages.error(request, 'Material no encontrado.')
        except (ValueError, TypeError) as e:
            messages.error(request, str(e))
    return redirect('detalle_orden', pk=orden_pk)