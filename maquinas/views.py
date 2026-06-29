from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from usuarios.permisos import es_admin, es_admin_o_tecnico
from .models import Maquina, Pieza, TransferenciaPieza, CodigoParada, ReasignacionPieza
from .forms import MaquinaForm, EnsambleForm, PiezaForm, TransferenciaPiezaForm, CodigoParadaForm, ReasignarPiezaForm


# ── Máquinas ──────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def lista_maquinas(request):
    maquinas = Maquina.objects.select_related('responsable').all()
    context = {
        'maquinas': maquinas,
        'total': maquinas.count(),
        'operativas': maquinas.filter(estado='OPERATIVA').count(),
        'en_mantenimiento': maquinas.filter(estado='MANTENIMIENTO').count(),
        'de_baja': maquinas.filter(estado='BAJA').count(),
        'es_admin': es_admin(request.user),
    }
    return render(request, 'maquinas/lista_maquinas.html', context)


from .models import Maquina, Pieza, TransferenciaPieza

@login_required(login_url='login')
def detalle_maquina(request, pk):
    maquina = get_object_or_404(Maquina, pk=pk)
    ensambles = maquina.piezas.filter(
        es_ensamble=True, activo=True
    ).prefetch_related('piezas_hijas')
    piezas_sin_ensamble = maquina.piezas.filter(
        es_ensamble=False, ensamble__isnull=True, activo=True
    )
    total_piezas = maquina.piezas.filter(activo=True).count()
    transferencias = TransferenciaPieza.objects.filter(
        Q(maquina_origen=maquina) | Q(maquina_destino=maquina)
    ).select_related('pieza', 'maquina_origen', 'maquina_destino', 'autorizado_por').order_by('-fecha')[:20]
    reasignaciones = ReasignacionPieza.objects.filter(
        pieza__maquina=maquina, pieza__activo=True
    ).select_related('pieza', 'ensamble_anterior', 'ensamble_nuevo', 'realizado_por').order_by('-fecha')[:20]
    context = {
        'maquina': maquina,
        'ensambles': ensambles,
        'piezas_sin_ensamble': piezas_sin_ensamble,
        'total_piezas': total_piezas,
        'transferencias': transferencias,
        'reasignaciones': reasignaciones,
        'es_admin': es_admin(request.user),
        'es_admin_o_tecnico': es_admin_o_tecnico(request.user),
    }
    return render(request, 'maquinas/detalle_maquina.html', context)


@login_required(login_url='login')
def crear_maquina(request):
    if not es_admin(request.user):
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('lista_maquinas')

    if request.method == 'POST':
        form = MaquinaForm(request.POST, request.FILES)
        if form.is_valid():
            maquina = form.save()
            messages.success(request, f'Máquina "{maquina.nombre}" creada correctamente.')
            return redirect('detalle_maquina', pk=maquina.pk)
    else:
        form = MaquinaForm()

    return render(request, 'maquinas/form_maquina.html', context={
        'form': form,
        'titulo': 'Nueva máquina',
        'accion': 'Crear',
    })


@login_required(login_url='login')
def editar_maquina(request, pk):
    if not es_admin(request.user):
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('detalle_maquina', pk=pk)

    maquina = get_object_or_404(Maquina, pk=pk)

    if request.method == 'POST':
        form = MaquinaForm(request.POST, request.FILES, instance=maquina)
        if form.is_valid():
            form.save()
            messages.success(request, f'Máquina "{maquina.nombre}" actualizada correctamente.')
            return redirect('detalle_maquina', pk=maquina.pk)
    else:
        form = MaquinaForm(instance=maquina)

    return render(request, 'maquinas/form_maquina.html', context={
        'form': form,
        'maquina': maquina,
        'titulo': f'Editar — {maquina.nombre}',
        'accion': 'Guardar cambios',
    })


@login_required(login_url='login')
def eliminar_maquina(request, pk):
    if not es_admin(request.user):
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('detalle_maquina', pk=pk)

    maquina = get_object_or_404(Maquina, pk=pk)

    if request.method == 'POST':
        maquina.estado = 'BAJA'
        maquina.save()
        messages.success(request, f'Máquina "{maquina.nombre}" desactivada del sistema.')
        return redirect('lista_maquinas')

    return render(request, 'maquinas/confirmar_eliminar_maquina.html', {'maquina': maquina})


@login_required(login_url='login')
def cambiar_estado_maquina(request, pk):
    if not es_admin(request.user):
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('detalle_maquina', pk=pk)

    maquina = get_object_or_404(Maquina, pk=pk)

    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado in ['OPERATIVA', 'MANTENIMIENTO', 'BAJA']:
            maquina.estado = nuevo_estado
            maquina.save()
            messages.success(request, f'Estado de "{maquina.nombre}" actualizado a {maquina.get_estado_display()}.')
        else:
            messages.error(request, 'Estado inválido.')
        return redirect('detalle_maquina', pk=maquina.pk)

    return redirect('detalle_maquina', pk=pk)


# ── Ensambles ─────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def crear_ensamble(request, maquina_pk):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('detalle_maquina', pk=maquina_pk)

    maquina = get_object_or_404(Maquina, pk=maquina_pk)

    if request.method == 'POST':
        form = EnsambleForm(request.POST)
        if form.is_valid():
            ensamble = form.save(commit=False)
            ensamble.maquina = maquina
            ensamble.es_ensamble = True
            ensamble.ensamble = None
            ensamble.save()
            messages.success(request, f'Ensamble "{ensamble.nombre}" creado correctamente.')
            return redirect('detalle_maquina', pk=maquina.pk)
    else:
        form = EnsambleForm()

    return render(request, 'maquinas/form_ensamble.html', {
        'form': form,
        'maquina': maquina,
        'titulo': f'Nuevo ensamble — {maquina.nombre}',
        'accion': 'Crear ensamble',
    })


# ── Piezas ────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def crear_pieza(request, maquina_pk):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('detalle_maquina', pk=maquina_pk)

    maquina = get_object_or_404(Maquina, pk=maquina_pk)

    if request.method == 'POST':
        form = PiezaForm(request.POST, request.FILES, maquina=maquina)
        if form.is_valid():
            pieza = form.save(commit=False)
            pieza.maquina = maquina
            pieza.es_ensamble = False
            pieza.save()
            messages.success(request, f'Pieza "{pieza.nombre}" registrada correctamente.')
            return redirect('detalle_maquina', pk=maquina.pk)
    else:
        form = PiezaForm(maquina=maquina)

    return render(request, 'maquinas/form_pieza.html', {
        'form': form,
        'maquina': maquina,
        'titulo': f'Nueva pieza — {maquina.nombre}',
        'accion': 'Registrar',
    })


@login_required(login_url='login')
def editar_pieza(request, pk):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('lista_maquinas')

    pieza = get_object_or_404(Pieza, pk=pk, activo=True)
    maquina = pieza.maquina

    if pieza.es_ensamble:
        FormClass = EnsambleForm
        template = 'maquinas/form_ensamble.html'
        nombre_tipo = 'ensamble'
    else:
        FormClass = PiezaForm
        template = 'maquinas/form_pieza.html'
        nombre_tipo = 'pieza'

    form_kwargs = {'instance': pieza}
    if FormClass is PiezaForm:
        form_kwargs['maquina'] = maquina

    if request.method == 'POST':
        form = FormClass(request.POST, request.FILES, **form_kwargs)
        if form.is_valid():
            form.save()
            messages.success(request, f'{nombre_tipo.capitalize()} "{pieza.nombre}" actualizado correctamente.')
            return redirect('detalle_maquina', pk=maquina.pk)
    else:
        form = FormClass(**form_kwargs)

    return render(request, template, {
        'form': form,
        'pieza': pieza,
        'maquina': maquina,
        'titulo': f'Editar {nombre_tipo} — {pieza.nombre}',
        'accion': 'Guardar cambios',
    })


@login_required(login_url='login')
def eliminar_pieza(request, pk):
    if not es_admin(request.user):
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('lista_maquinas')

    pieza = get_object_or_404(Pieza, pk=pk, activo=True)
    maquina = pieza.maquina

    if request.method == 'POST':
        n_hijas = 0
        if pieza.es_ensamble:
            n_hijas = pieza.piezas_hijas.filter(activo=True).count()
            pieza.piezas_hijas.filter(activo=True).update(activo=False)
        pieza.activo = False
        pieza.save()
        sufijo = f' junto con sus {n_hijas} pieza{"s" if n_hijas != 1 else ""} hija{"s" if n_hijas != 1 else ""}' if n_hijas else ''
        messages.success(request, f'"{pieza.nombre}"{sufijo} eliminada correctamente.')
        return redirect('detalle_maquina', pk=maquina.pk)

    return render(request, 'maquinas/confirmar_eliminar_pieza.html', {
        'pieza': pieza,
        'maquina': maquina,
    })


# ── Códigos de parada ─────────────────────────────────────────────────────────

@login_required(login_url='login')
def lista_codigos_parada(request):
    qs = CodigoParada.objects.all().order_by('fabricante', 'modelo_maquina', 'tipo', 'codigo')

    # Filtros GET opcionales
    fabricante     = request.GET.get('fabricante', '').strip()
    modelo_maquina = request.GET.get('modelo', '').strip()
    if fabricante:
        qs = qs.filter(fabricante__icontains=fabricante)
    if modelo_maquina:
        qs = qs.filter(modelo_maquina__icontains=modelo_maquina)

    fabricantes_distintos = CodigoParada.objects.values_list(
        'fabricante', flat=True
    ).distinct().order_by('fabricante')
    modelos_distintos = CodigoParada.objects.values_list(
        'modelo_maquina', flat=True
    ).distinct().order_by('modelo_maquina')

    context = {
        'codigos':              qs,
        'total':                qs.count(),
        'planificados':         qs.filter(tipo='PLANIFICADA').count(),
        'no_planificados':      qs.filter(tipo='NO_PLANIFICADA').count(),
        'fabricantes':          fabricantes_distintos,
        'modelos':              modelos_distintos,
        'filtro_fabricante':    fabricante,
        'filtro_modelo':        modelo_maquina,
        'es_admin_o_tecnico':   es_admin_o_tecnico(request.user),
    }
    return render(request, 'maquinas/lista_codigos_parada.html', context)


@login_required(login_url='login')
def detalle_codigo_parada(request, pk):
    codigo = get_object_or_404(CodigoParada, pk=pk)
    usos   = codigo.registros.select_related(
        'orden_trabajo__reserva__maquina'
    ).order_by('-fecha_creacion')[:15]
    context = {
        'codigo':             codigo,
        'usos':               usos,
        'total_usos':         codigo.registros.count(),
        'es_admin':           es_admin(request.user),
        'es_admin_o_tecnico': es_admin_o_tecnico(request.user),
    }
    return render(request, 'maquinas/detalle_codigo_parada.html', context)


@login_required(login_url='login')
def crear_codigo_parada(request):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para crear códigos de parada.')
        return redirect('lista_codigos_parada')

    if request.method == 'POST':
        form = CodigoParadaForm(request.POST)
        if form.is_valid():
            cp = form.save()
            messages.success(
                request,
                f'Código "{cp.codigo}" para {cp.fabricante} {cp.modelo_maquina} creado correctamente.'
            )
            return redirect('detalle_codigo_parada', pk=cp.pk)
    else:
        # Pre-rellenar fabricante/modelo si vienen por GET (desde detalle_maquina)
        initial = {
            'fabricante':     request.GET.get('fabricante', ''),
            'modelo_maquina': request.GET.get('modelo', ''),
        }
        form = CodigoParadaForm(initial=initial)

    return render(request, 'maquinas/form_codigo_parada.html', {
        'form':   form,
        'titulo': 'Nuevo código de parada',
        'accion': 'Crear código',
    })


@login_required(login_url='login')
def editar_codigo_parada(request, pk):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para editar códigos de parada.')
        return redirect('detalle_codigo_parada', pk=pk)

    codigo = get_object_or_404(CodigoParada, pk=pk)

    if request.method == 'POST':
        form = CodigoParadaForm(request.POST, instance=codigo)
        if form.is_valid():
            form.save()
            messages.success(request, f'Código "{codigo.codigo}" actualizado correctamente.')
            return redirect('detalle_codigo_parada', pk=codigo.pk)
    else:
        form = CodigoParadaForm(instance=codigo)

    return render(request, 'maquinas/form_codigo_parada.html', {
        'form':   form,
        'codigo': codigo,
        'titulo': f'Editar — [{codigo.modelo_maquina}] {codigo.codigo}',
        'accion': 'Guardar cambios',
    })


@login_required(login_url='login')
def eliminar_codigo_parada(request, pk):
    if not es_admin(request.user):
        messages.error(request, 'No tienes permisos para eliminar códigos de parada.')
        return redirect('detalle_codigo_parada', pk=pk)

    codigo = get_object_or_404(CodigoParada, pk=pk)

    if request.method == 'POST':
        nombre = f'[{codigo.modelo_maquina}] {codigo.codigo}'
        codigo.delete()
        messages.success(request, f'Código "{nombre}" eliminado correctamente.')
        return redirect('lista_codigos_parada')

    return render(request, 'maquinas/confirmar_eliminar_codigo_parada.html', {'codigo': codigo})


# ── Transferencias ────────────────────────────────────────────────────────────

@login_required(login_url='login')
def lista_transferencias(request):
    qs = TransferenciaPieza.objects.select_related(
        'pieza', 'maquina_origen', 'maquina_destino', 'autorizado_por'
    ).order_by('-fecha')

    maquina_pk = request.GET.get('maquina', '')
    pieza_pk   = request.GET.get('pieza', '')
    desde      = request.GET.get('desde', '')
    hasta      = request.GET.get('hasta', '')

    if maquina_pk:
        qs = qs.filter(
            Q(maquina_origen__pk=maquina_pk) |
            Q(maquina_destino__pk=maquina_pk)
        )
    if pieza_pk:
        qs = qs.filter(pieza__pk=pieza_pk)
    if desde:
        qs = qs.filter(fecha__date__gte=desde)
    if hasta:
        qs = qs.filter(fecha__date__lte=hasta)

    total        = qs.count()
    piezas_dist  = qs.values('pieza').distinct().count()
    maquinas_mov = (
        qs.values('maquina_destino').distinct().count()
    )

    maquinas = Maquina.objects.exclude(estado='BAJA').order_by('nombre')
    piezas   = Pieza.objects.filter(activo=True).order_by('nombre')

    return render(request, 'maquinas/lista_transferencias.html', {
        'transferencias': qs[:200],
        'total':          total,
        'piezas_dist':    piezas_dist,
        'maquinas_mov':   maquinas_mov,
        'maquinas':       maquinas,
        'piezas':         piezas,
        'filtro_maquina': maquina_pk,
        'filtro_pieza':   pieza_pk,
        'filtro_desde':   desde,
        'filtro_hasta':   hasta,
        'hay_filtros':    any([maquina_pk, pieza_pk, desde, hasta]),
    })


@login_required(login_url='login')
def crear_transferencia(request, pieza_pk):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('lista_maquinas')

    pieza = get_object_or_404(Pieza, pk=pieza_pk, activo=True)

    if request.method == 'POST':
        form = TransferenciaPiezaForm(request.POST, pieza=pieza)
        if form.is_valid():
            transferencia = form.save(commit=False)
            transferencia.pieza = pieza
            transferencia.maquina_origen = pieza.maquina
            transferencia.autorizado_por = request.user
            # Reasignar la pieza a la máquina destino
            pieza.maquina = transferencia.maquina_destino
            if pieza.es_ensamble:
                # Sus piezas hijas viajan con él para no quedar huérfanas
                pieza.piezas_hijas.filter(activo=True).update(maquina=transferencia.maquina_destino)
            else:
                # Se asigna al ensamble elegido en destino, o queda suelta si no se eligió ninguno
                # (un ensamble no puede tener piezas de otra máquina)
                pieza.ensamble = form.cleaned_data.get('ensamble_destino')
            pieza.save()
            transferencia.save()
            messages.success(request, f'Pieza "{pieza.nombre}" transferida correctamente.')
            return redirect('detalle_maquina', pk=transferencia.maquina_destino.pk)
    else:
        form = TransferenciaPiezaForm(pieza=pieza)

    return render(request, 'maquinas/form_transferencia.html', {
        'form': form,
        'pieza': pieza,
        'maquina_origen': pieza.maquina,
    })


@login_required(login_url='login')
def reasignar_pieza(request, pk):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('lista_maquinas')

    pieza = get_object_or_404(Pieza, pk=pk, activo=True, es_ensamble=False)
    maquina = pieza.maquina

    if request.method == 'POST':
        form = ReasignarPiezaForm(request.POST, pieza=pieza)
        if form.is_valid():
            ensamble_anterior = pieza.ensamble
            ensamble_nuevo = form.cleaned_data.get('ensamble_nuevo')
            pieza.ensamble = ensamble_nuevo
            pieza.save()
            ReasignacionPieza.objects.create(
                pieza=pieza,
                ensamble_anterior=ensamble_anterior,
                ensamble_nuevo=ensamble_nuevo,
                realizado_por=request.user,
            )
            if ensamble_nuevo:
                messages.success(request, f'"{pieza.nombre}" asignada al ensamble "{ensamble_nuevo.nombre}".')
            else:
                messages.success(request, f'"{pieza.nombre}" desvinculada — queda como pieza suelta.')
            return redirect('detalle_maquina', pk=maquina.pk)
    else:
        form = ReasignarPiezaForm(pieza=pieza, initial={'ensamble_nuevo': pieza.ensamble})

    return render(request, 'maquinas/reasignar_pieza.html', {
        'form': form,
        'pieza': pieza,
        'maquina': maquina,
    })


@login_required(login_url='login')
def detalle_pieza(request, pk):
    pieza = get_object_or_404(Pieza, pk=pk, activo=True)
    maquina = pieza.maquina
    transferencias = TransferenciaPieza.objects.filter(
        pieza=pieza
    ).select_related('maquina_origen', 'maquina_destino', 'autorizado_por').order_by('-fecha')
    reasignaciones = ReasignacionPieza.objects.filter(
        pieza=pieza
    ).select_related('ensamble_anterior', 'ensamble_nuevo', 'realizado_por').order_by('-fecha')
    context = {
        'pieza': pieza,
        'maquina': maquina,
        'transferencias': transferencias,
        'reasignaciones': reasignaciones,
        'es_admin': es_admin(request.user),
        'es_admin_o_tecnico': es_admin_o_tecnico(request.user),
    }
    return render(request, 'maquinas/detalle_pieza.html', context)