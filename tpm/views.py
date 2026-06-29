from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from usuarios.permisos import es_admin, es_admin_o_tecnico
from .models import (
    CertificacionUsuario, InspeccionDiaria,
    RegistroOEE, Incidente, Alerta, HallazgoInspeccion,
    ItemChecklistInspeccion,
)
from .forms import CertificacionForm, IncidenteForm, HallazgoForm, ItemChecklistForm


# ── DASHBOARD TPM ─────────────────────────────────────────────────────────────

@login_required(login_url='login')
def dashboard_tpm(request):
    hoy = timezone.now().date()
    context = {
        'total_inspecciones':       InspeccionDiaria.objects.count(),
        'inspecciones_hoy':         InspeccionDiaria.objects.filter(fecha=hoy).count(),
        'inspecciones_fallidas':    InspeccionDiaria.objects.filter(aprobada=False).count(),
        'certificaciones_vencidas': CertificacionUsuario.objects.filter(
            fecha_vencimiento__lt=hoy, activo=True
        ).count(),
        'certificaciones_por_vencer': CertificacionUsuario.objects.filter(
            fecha_vencimiento__gte=hoy,
            fecha_vencimiento__lte=hoy + timezone.timedelta(days=30),
            activo=True
        ).count(),
        'incidentes_criticos': Incidente.objects.filter(severidad='CRITICA', activo=True).count(),
        'alertas_activas':     Alerta.objects.filter(resuelta=False).count(),
        'alertas_criticas':    Alerta.objects.filter(resuelta=False, severidad='CRITICA').count(),
        'ultimas_alertas':     Alerta.objects.filter(resuelta=False).select_related('maquina')[:8],
        'ultimas_inspecciones': InspeccionDiaria.objects.select_related(
            'maquina', 'inspector'
        ).order_by('-fecha')[:5],
        'ultimo_oee': RegistroOEE.objects.select_related('maquina').first(),
        'es_admin_o_tecnico': es_admin_o_tecnico(request.user),
    }
    return render(request, 'tpm/dashboard_tpm.html', context)


# ── INSPECCIONES ──────────────────────────────────────────────────────────────

@login_required(login_url='login')
def lista_inspecciones(request):
    inspecciones = InspeccionDiaria.objects.select_related('maquina', 'inspector').prefetch_related('respuestas_checklist').all()
    context = {
        'inspecciones': inspecciones,
        'total':        inspecciones.count(),
        'aprobadas':    inspecciones.filter(aprobada=True).count(),
        'fallidas':     inspecciones.filter(aprobada=False).count(),
    }
    return render(request, 'tpm/lista_inspecciones.html', context)


@login_required(login_url='login')
def detalle_inspeccion(request, pk):
    inspeccion = get_object_or_404(
        InspeccionDiaria.objects.select_related('maquina', 'inspector').prefetch_related('respuestas_checklist__item'),
        pk=pk
    )
    context = {
        'inspeccion':         inspeccion,
        'hallazgos':          inspeccion.hallazgos.all().order_by('-fecha_creacion'),
        'hallazgo_form':      HallazgoForm(),
        'es_admin_o_tecnico': es_admin_o_tecnico(request.user),
    }
    return render(request, 'tpm/detalle_inspeccion.html', context)


# ── HALLAZGOS DE INSPECCIÓN ───────────────────────────────────────────────────

@login_required(login_url='login')
def agregar_hallazgo(request, inspeccion_pk):
    inspeccion = get_object_or_404(InspeccionDiaria, pk=inspeccion_pk)
    if request.method == 'POST':
        form = HallazgoForm(request.POST)
        if form.is_valid():
            hallazgo            = form.save(commit=False)
            hallazgo.inspeccion = inspeccion
            hallazgo.save()
            messages.success(request, 'Hallazgo registrado correctamente.')
        else:
            detalle = '; '.join(
                '; '.join(errores) for errores in form.errors.values()
            )
            messages.error(request, f'Error al registrar hallazgo: {detalle}')
    return redirect('detalle_inspeccion', pk=inspeccion_pk)


@login_required(login_url='login')
def editar_hallazgo(request, pk):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para editar hallazgos.')
        return redirect('lista_inspecciones')

    hallazgo = get_object_or_404(HallazgoInspeccion, pk=pk)

    if request.method == 'POST':
        form = HallazgoForm(request.POST, instance=hallazgo)
        if form.is_valid():
            form.save()
            messages.success(request, 'Hallazgo actualizado correctamente.')
            return redirect('detalle_inspeccion', pk=hallazgo.inspeccion.pk)
    else:
        form = HallazgoForm(instance=hallazgo)

    return render(request, 'tpm/form_hallazgo.html', {
        'form':      form,
        'hallazgo':  hallazgo,
        'titulo':    f'Editar hallazgo — Inspección #{hallazgo.inspeccion.pk}',
        'accion':    'Guardar cambios',
    })


@login_required(login_url='login')
def resolver_hallazgo(request, pk):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para resolver hallazgos.')
        return redirect('lista_inspecciones')

    hallazgo = get_object_or_404(HallazgoInspeccion, pk=pk)
    if request.method == 'POST':
        hallazgo.resuelto = not hallazgo.resuelto
        hallazgo.save(update_fields=['resuelto'])
        estado = 'resuelto' if hallazgo.resuelto else 'reabierto'
        messages.success(request, f'Hallazgo marcado como {estado}.')
    return redirect('detalle_inspeccion', pk=hallazgo.inspeccion.pk)


@login_required(login_url='login')
def eliminar_hallazgo(request, pk):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para eliminar hallazgos.')
        return redirect('lista_inspecciones')

    hallazgo   = get_object_or_404(HallazgoInspeccion, pk=pk)
    inspeccion_pk = hallazgo.inspeccion.pk
    if request.method == 'POST':
        hallazgo.delete()
        messages.success(request, 'Hallazgo eliminado correctamente.')
    return redirect('detalle_inspeccion', pk=inspeccion_pk)


# ── CATÁLOGO DE ÍTEMS DE CHECKLIST (por fabricante+modelo) ────────────────────
# Mismo patrón que CodigoParada en maquinas/views.py: catálogo scopeado,
# no por máquina individual.

@login_required(login_url='login')
def lista_items_checklist(request):
    qs = ItemChecklistInspeccion.objects.all()

    fabricante     = request.GET.get('fabricante', '').strip()
    modelo_maquina = request.GET.get('modelo', '').strip()
    if fabricante:
        qs = qs.filter(fabricante__icontains=fabricante)
    if modelo_maquina:
        qs = qs.filter(modelo_maquina__icontains=modelo_maquina)

    fabricantes_distintos = ItemChecklistInspeccion.objects.values_list(
        'fabricante', flat=True
    ).distinct().order_by('fabricante')
    modelos_distintos = ItemChecklistInspeccion.objects.values_list(
        'modelo_maquina', flat=True
    ).distinct().order_by('modelo_maquina')

    context = {
        'items':                qs,
        'total':                qs.count(),
        'criticos':             qs.filter(es_critico=True).count(),
        'fabricantes':          fabricantes_distintos,
        'modelos':              modelos_distintos,
        'filtro_fabricante':    fabricante,
        'filtro_modelo':        modelo_maquina,
        'es_admin_o_tecnico':   es_admin_o_tecnico(request.user),
    }
    return render(request, 'tpm/lista_items_checklist.html', context)


@login_required(login_url='login')
def crear_item_checklist(request):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para crear ítems de checklist.')
        return redirect('lista_items_checklist')

    if request.method == 'POST':
        form = ItemChecklistForm(request.POST)
        if form.is_valid():
            item = form.save()
            messages.success(
                request,
                f'Ítem "{item.nombre}" agregado al checklist de {item.fabricante} {item.modelo_maquina}.'
            )
            return redirect('lista_items_checklist')
    else:
        initial = {
            'fabricante':     request.GET.get('fabricante', ''),
            'modelo_maquina': request.GET.get('modelo', ''),
        }
        form = ItemChecklistForm(initial=initial)

    return render(request, 'tpm/form_item_checklist.html', {
        'form':   form,
        'titulo': 'Nuevo ítem de checklist',
        'accion': 'Crear ítem',
    })


@login_required(login_url='login')
def editar_item_checklist(request, pk):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para editar ítems de checklist.')
        return redirect('lista_items_checklist')

    item = get_object_or_404(ItemChecklistInspeccion, pk=pk)

    if request.method == 'POST':
        form = ItemChecklistForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f'Ítem "{item.nombre}" actualizado correctamente.')
            return redirect('lista_items_checklist')
    else:
        form = ItemChecklistForm(instance=item)

    return render(request, 'tpm/form_item_checklist.html', {
        'form':   form,
        'item':   item,
        'titulo': f'Editar — {item.nombre}',
        'accion': 'Guardar cambios',
    })


@login_required(login_url='login')
def eliminar_item_checklist(request, pk):
    if not es_admin(request.user):
        messages.error(request, 'No tienes permisos para eliminar ítems de checklist.')
        return redirect('lista_items_checklist')

    item = get_object_or_404(ItemChecklistInspeccion, pk=pk)

    if request.method == 'POST':
        nombre = item.nombre
        item.delete()
        messages.success(request, f'Ítem "{nombre}" eliminado correctamente.')
        return redirect('lista_items_checklist')

    return render(request, 'tpm/confirmar_eliminar_item_checklist.html', {'item': item})


# ── CERTIFICACIONES ───────────────────────────────────────────────────────────

@login_required(login_url='login')
def lista_certificaciones(request):
    hoy   = timezone.now().date()
    certs = list(CertificacionUsuario.objects.select_related(
        'usuario', 'maquina', 'otorgado_por'
    ).filter(activo=True).order_by('fecha_vencimiento'))

    es_admin_actual           = es_admin(request.user)
    es_admin_o_tecnico_actual = es_admin_o_tecnico(request.user)
    for c in certs:
        es_propia = c.usuario_id == request.user.pk
        objetivo_es_admin_o_tecnico = c.usuario is not None and es_admin_o_tecnico(c.usuario)
        c.puede_revocar = (
            es_propia
            or es_admin_actual
            or (es_admin_o_tecnico_actual and not objetivo_es_admin_o_tecnico)
        )
        c.puede_editar = es_admin_o_tecnico_actual and not es_propia

    context = {
        'certificaciones':    certs,
        'total':              len(certs),
        'vigentes':           sum(1 for c in certs if c.vigente),
        'vencidas':           sum(1 for c in certs if not c.vigente),
        'por_vencer':         sum(
            1 for c in certs if hoy <= c.fecha_vencimiento <= hoy + timezone.timedelta(days=30)
        ),
        'es_admin_o_tecnico': es_admin_o_tecnico_actual,
    }
    return render(request, 'tpm/lista_certificaciones.html', context)


@login_required(login_url='login')
def crear_certificacion(request):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para otorgar certificaciones.')
        return redirect('lista_certificaciones')
    if request.method == 'POST':
        form = CertificacionForm(request.POST, usuario_actual=request.user)
        if form.is_valid():
            cert = form.save(commit=False)
            cert.otorgado_por = request.user
            cert.activo       = True
            cert.save()
            messages.success(
                request,
                f'Certificación otorgada a {cert.usuario.username if cert.usuario else "usuario eliminado"} para {cert.maquina.nombre}.'
            )
            return redirect('lista_certificaciones')
    else:
        form = CertificacionForm(usuario_actual=request.user)
    return render(request, 'tpm/form_certificacion.html', {
        'form':   form,
        'titulo': 'Nueva certificación',
        'accion': 'Otorgar certificación',
    })


@login_required(login_url='login')
def editar_certificacion(request, pk):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para editar certificaciones.')
        return redirect('lista_certificaciones')
    cert = get_object_or_404(CertificacionUsuario, pk=pk)
    if cert.usuario_id == request.user.pk:
        messages.error(
            request,
            'No puedes editar tu propia certificación (incluye extender la fecha de vencimiento). '
            'Otra persona calificada debe hacerlo.'
        )
        return redirect('lista_certificaciones')
    if request.method == 'POST':
        form = CertificacionForm(request.POST, instance=cert, usuario_actual=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Certificación actualizada correctamente.')
            return redirect('lista_certificaciones')
    else:
        form = CertificacionForm(instance=cert, usuario_actual=request.user)
    return render(request, 'tpm/form_certificacion.html', {
        'form':   form,
        'cert':   cert,
        'titulo': f'Editar certificación — {cert.usuario.username if cert.usuario else "usuario eliminado"}',
        'accion': 'Guardar cambios',
    })


@login_required(login_url='login')
def revocar_certificacion(request, pk):
    cert = get_object_or_404(CertificacionUsuario, pk=pk)

    es_propia = cert.usuario_id == request.user.pk
    objetivo_es_admin_o_tecnico = cert.usuario is not None and es_admin_o_tecnico(cert.usuario)
    puede = (
        es_propia
        or es_admin(request.user)
        or (es_admin_o_tecnico(request.user) and not objetivo_es_admin_o_tecnico)
    )
    if not puede:
        messages.error(
            request,
            'Solo un administrador puede revocar la certificación de otro técnico o administrador.'
        )
        return redirect('lista_certificaciones')

    if request.method == 'POST':
        cert.activo = False
        cert.save(update_fields=['activo'])
        usuario_str = cert.usuario.username if cert.usuario else 'usuario eliminado'
        messages.success(
            request,
            f'Certificación de {usuario_str} para {cert.maquina.nombre} revocada.'
        )
        return redirect('lista_certificaciones')
    return render(request, 'tpm/confirmar_revocar_certificacion.html', {'cert': cert})


# ── INCIDENTES ────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def lista_incidentes(request):
    incidentes = Incidente.objects.select_related('maquina', 'reportado_por').filter(activo=True)
    context = {
        'incidentes':         incidentes,
        'total':              incidentes.count(),
        'criticos':           incidentes.filter(severidad='CRITICA').count(),
        'requieren_mto':      incidentes.filter(requiere_mantenimiento=True).count(),
        'es_admin_o_tecnico': es_admin_o_tecnico(request.user),
    }
    return render(request, 'tpm/lista_incidentes.html', context)


@login_required(login_url='login')
def crear_incidente(request):
    if request.method == 'POST':
        form = IncidenteForm(request.POST)
        if form.is_valid():
            incidente = form.save(commit=False)
            incidente.reportado_por = request.user
            incidente.activo        = True
            incidente.save()
            messages.success(
                request,
                f'Incidente registrado en {incidente.maquina.nombre}.'
                + (' Se generó una alerta de mantenimiento.' if incidente.requiere_mantenimiento else '')
            )
            return redirect('detalle_incidente', pk=incidente.pk)
    else:
        # Pre-cargar fecha actual como valor por defecto
        now_str = timezone.now().strftime('%Y-%m-%dT%H:%M')
        form = IncidenteForm(initial={'fecha_ocurrencia': now_str})

    return render(request, 'tpm/form_incidente.html', {
        'form':   form,
        'titulo': 'Registrar incidente',
        'accion': 'Registrar incidente',
    })


@login_required(login_url='login')
def detalle_incidente(request, pk):
    incidente = get_object_or_404(
        Incidente.objects.select_related('maquina', 'reportado_por'),
        pk=pk, activo=True
    )
    return render(request, 'tpm/detalle_incidente.html', {
        'incidente':          incidente,
        'es_admin_o_tecnico': es_admin_o_tecnico(request.user),
    })


@login_required(login_url='login')
def editar_incidente(request, pk):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para editar incidentes.')
        return redirect('detalle_incidente', pk=pk)

    incidente = get_object_or_404(Incidente, pk=pk, activo=True)

    if request.method == 'POST':
        requeria_mto_antes = incidente.requiere_mantenimiento
        form = IncidenteForm(request.POST, instance=incidente)
        if form.is_valid():
            incidente_actualizado = form.save()
            # Si se activó "requiere_mantenimiento" en la edición, generar la alerta
            # (el signal solo la crea en created=True)
            if not requeria_mto_antes and incidente_actualizado.requiere_mantenimiento:
                from tpm.models import Alerta
                Alerta.objects.create(
                    tipo='INCIDENTE',
                    severidad='CRITICA',
                    maquina=incidente_actualizado.maquina,
                    referencia_id=incidente_actualizado.pk,
                    referencia_tipo='Incidente',
                    mensaje=(
                        f"Incidente en {incidente_actualizado.maquina.nombre} requiere mantenimiento: "
                        f"{incidente_actualizado.get_tipo_display()} — "
                        f"{incidente_actualizado.descripcion[:100]}"
                    ),
                )
            messages.success(request, f'Incidente #{incidente.pk} actualizado correctamente.')
            return redirect('detalle_incidente', pk=incidente.pk)
    else:
        form = IncidenteForm(instance=incidente)
        # Rellenar el datetime-local con el formato correcto
        form.initial['fecha_ocurrencia'] = incidente.fecha_ocurrencia.strftime('%Y-%m-%dT%H:%M')

    return render(request, 'tpm/form_incidente.html', {
        'form':      form,
        'incidente': incidente,
        'titulo':    f'Editar incidente #{incidente.pk}',
        'accion':    'Guardar cambios',
    })


# ── OEE ───────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def lista_oee(request):
    registros = RegistroOEE.objects.select_related('maquina').filter(activo=True)
    context = {
        'registros':          registros,
        'total':              registros.count(),
        'es_admin_o_tecnico': es_admin_o_tecnico(request.user),
    }
    return render(request, 'tpm/lista_oee.html', context)


@login_required(login_url='login')
def calcular_oee(request):
    """
    Calcula el OEE de una máquina para un mes/año dado,
    agregando todas las órdenes de trabajo FINALIZADAS de ese período.

    Fórmulas:
      Disponibilidad = (Σ tiempo_real_min) / (Σ tiempo_planificado_min) × 100
      Rendimiento    = (Σ unidades_producidas) / (Σ unidades_esperadas) × 100
      Calidad        = (Σ unidades_sin_defecto) / (Σ unidades_producidas) × 100
      OEE            = (D × R × C) / 10 000
    """
    from maquinas.models import Maquina
    from reservas.models import OrdenTrabajo
    from django.db.models import Sum

    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para calcular el OEE.')
        return redirect('lista_oee')

    maquinas = Maquina.objects.filter(estado='OPERATIVA').order_by('nombre')
    hoy      = timezone.now().date()

    # Resultados del cálculo (si se envió el formulario)
    resultado = None
    errores   = []

    if request.method == 'POST':
        maquina_id = request.POST.get('maquina')
        mes_str    = request.POST.get('mes')
        anio_str   = request.POST.get('anio')

        try:
            maquina = Maquina.objects.get(pk=maquina_id)
            mes     = int(mes_str)
            anio    = int(anio_str)

            if not (1 <= mes <= 12):
                raise ValueError('El mes debe estar entre 1 y 12.')
            if anio < 2020 or anio > hoy.year:
                raise ValueError(f'El año debe estar entre 2020 y {hoy.year}.')

        except (Maquina.DoesNotExist, TypeError, ValueError) as e:
            messages.error(request, f'Datos inválidos: {e}')
            return render(request, 'tpm/calcular_oee.html', {
                'maquinas': maquinas, 'hoy': hoy,
            })

        # Órdenes del período para esa máquina
        ordenes = OrdenTrabajo.objects.filter(
            estado='FINALIZADA',
            reserva__maquina=maquina,
            reserva__fecha__year=anio,
            reserva__fecha__month=mes,
            activo=True,
        )

        if not ordenes.exists():
            messages.warning(
                request,
                f'No hay órdenes de trabajo finalizadas para {maquina.nombre} '
                f'en {mes:02d}/{anio}. No se puede calcular el OEE.'
            )
            return render(request, 'tpm/calcular_oee.html', {
                'maquinas': maquinas, 'hoy': hoy,
            })

        # Agregar totales
        totales = ordenes.aggregate(
            t_plan  = Sum('tiempo_planificado_min'),
            t_real  = Sum('tiempo_real_min'),
            u_prod  = Sum('unidades_producidas'),
            u_esp   = Sum('unidades_esperadas'),
            u_ok    = Sum('unidades_sin_defecto'),
        )

        t_plan = float(totales['t_plan'] or 0)
        t_real = float(totales['t_real'] or 0)
        u_prod = float(totales['u_prod'] or 0)
        u_esp  = float(totales['u_esp']  or 0)
        u_ok   = float(totales['u_ok']   or 0)

        # Calcular componentes (evitar división por cero)
        disponibilidad = round((t_real / t_plan * 100), 2) if t_plan > 0 else 0
        rendimiento    = round((u_prod / u_esp  * 100), 2) if u_esp  > 0 else 0
        calidad        = round((u_ok   / u_prod * 100), 2) if u_prod > 0 else 0
        oee_calc       = round((disponibilidad * rendimiento * calidad) / 10000, 2)

        # Crear o actualizar el registro (unique_together: maquina+mes+anio)
        registro, creado = RegistroOEE.objects.update_or_create(
            maquina=maquina,
            mes=mes,
            anio=anio,
            defaults={
                'disponibilidad': disponibilidad,
                'rendimiento':    rendimiento,
                'calidad':        calidad,
                'observaciones':  f'Calculado automáticamente desde {ordenes.count()} OT finalizadas.',
                'activo':         True,
            }
        )

        accion = 'Creado' if creado else 'Actualizado'
        messages.success(
            request,
            f'{accion} OEE de {maquina.nombre} para {mes:02d}/{anio}: '
            f'D={disponibilidad}% | R={rendimiento}% | C={calidad}% → OEE={oee_calc}%'
        )

        resultado = {
            'maquina':        maquina,
            'mes':            mes,
            'anio':           anio,
            'ordenes_count':  ordenes.count(),
            'disponibilidad': disponibilidad,
            'rendimiento':    rendimiento,
            'calidad':        calidad,
            'oee':            oee_calc,
            't_plan':         round(t_plan, 1),
            't_real':         round(t_real, 1),
            'u_prod':         int(u_prod),
            'u_esp':          int(u_esp),
            'u_ok':           int(u_ok),
            'registro_pk':    registro.pk,
        }

    return render(request, 'tpm/calcular_oee.html', {
        'maquinas': maquinas,
        'hoy':      hoy,
        'resultado': resultado,
    })


# ── ALERTAS ───────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def lista_alertas(request):
    mostrar_resueltas = request.GET.get('resueltas') == '1'
    alertas = Alerta.objects.select_related(
        'maquina', 'asignado_a', 'resuelta_por'
    ).filter(resuelta=mostrar_resueltas)

    from usuarios.models import Usuario as UsuarioModel
    from django.db.models import Q
    tecnicos = UsuarioModel.objects.filter(estado='ACTIVO').exclude(
        is_superuser=True
    ).exclude(
        Q(rol__nombre__icontains='administrador') | Q(rol__nombre__icontains='phd')
    ).order_by('first_name', 'last_name')

    activas = Alerta.objects.filter(resuelta=False)
    context = {
        'alertas':            alertas,
        'total':              activas.count(),
        'criticas':           activas.filter(severidad='CRITICA').count(),
        'advertencias':       activas.filter(severidad='ADVERTENCIA').count(),
        'tecnicos':           tecnicos,
        'mostrar_resueltas':  mostrar_resueltas,
        'es_admin_o_tecnico': es_admin_o_tecnico(request.user),
        'es_admin':           es_admin(request.user),
    }
    return render(request, 'tpm/lista_alertas.html', context)


@login_required(login_url='login')
def resolver_alerta(request, pk):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para resolver alertas.')
        return redirect('lista_alertas')
    alerta = get_object_or_404(Alerta, pk=pk)
    if request.method == 'POST':
        nota = request.POST.get('nota_resolucion', '').strip()
        alerta.resolver(request.user, nota=nota)
        messages.success(request, 'Alerta resuelta y acción registrada.')
    return redirect('lista_alertas')


@login_required(login_url='login')
def asignar_alerta(request, pk):
    if not es_admin(request.user):
        messages.error(request, 'Solo un administrador puede asignar alertas a responsables.')
        return redirect('lista_alertas')
    alerta = get_object_or_404(Alerta, pk=pk)
    if request.method == 'POST':
        from usuarios.models import Usuario as UsuarioModel
        from django.db.models import Q
        from django.utils import timezone as tz
        usuario_id = request.POST.get('asignado_a')
        if usuario_id:
            try:
                # Verificar que el destino sea efectivamente un técnico/ingeniero, no admin
                usuario = UsuarioModel.objects.exclude(
                    Q(rol__nombre__icontains='administrador') | Q(rol__nombre__icontains='phd')
                ).get(pk=usuario_id)
                alerta.asignado_a  = usuario
                alerta.asignado_en = tz.now()
                alerta.save(update_fields=['asignado_a', 'asignado_en'])
                messages.success(request, f'Alerta asignada a {usuario.get_full_name() or usuario.username}.')
            except UsuarioModel.DoesNotExist:
                messages.error(request, 'Usuario no válido para asignación.')
    return redirect('lista_alertas')


@login_required(login_url='login')
def crear_om_desde_alerta(request, pk):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para crear órdenes de mantenimiento.')
        return redirect('lista_alertas')
    alerta = get_object_or_404(Alerta, pk=pk)
    if not alerta.puede_generar_om or not alerta.maquina:
        messages.error(request, 'Esta alerta no permite generar una orden de mantenimiento.')
        return redirect('lista_alertas')
    if request.method == 'POST':
        from django.utils import timezone as tz
        from mantenimiento.models import OrdenMantenimiento
        prioridad = 'ALTA' if alerta.severidad == 'CRITICA' else 'MEDIA'
        om = OrdenMantenimiento.objects.create(
            maquina=alerta.maquina,
            origen='MANUAL',
            tipo='CORRECTIVO',
            estado='PROGRAMADA',
            prioridad=prioridad,
            titulo=alerta.titulo_om_sugerido,
            descripcion_tarea=alerta.mensaje,
            fecha_programada=tz.now().date(),
            creado_por=request.user,
            activo=True,
        )
        messages.success(request, f'Orden {om.numero()} creada desde la alerta.')
        return redirect('detalle_orden_mantenimiento', pk=om.pk)
    return redirect('lista_alertas')