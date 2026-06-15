from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import (
    CertificacionUsuario, InspeccionDiaria,
    RegistroOEE, Incidente, Alerta
)
from .forms import CertificacionForm, IncidenteForm


def es_admin(user):
    if user.is_superuser:
        return True
    if user.rol:
        rol = user.rol.nombre.lower()
        return 'administrador' in rol or 'phd' in rol
    return False


def es_admin_o_tecnico(user):
    if user.is_superuser:
        return True
    if user.rol:
        rol = user.rol.nombre.lower()
        return any(r in rol for r in ['administrador', 'phd', 'técnico', 'ingeniero'])
    return False


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
    inspecciones = InspeccionDiaria.objects.select_related('maquina', 'inspector').all()
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
        InspeccionDiaria.objects.select_related('maquina', 'inspector'), pk=pk)
    context = {
        'inspeccion': inspeccion,
        'hallazgos':  inspeccion.hallazgos.all(),
    }
    return render(request, 'tpm/detalle_inspeccion.html', context)


# ── CERTIFICACIONES ───────────────────────────────────────────────────────────

@login_required(login_url='login')
def lista_certificaciones(request):
    hoy   = timezone.now().date()
    certs = CertificacionUsuario.objects.select_related(
        'usuario', 'maquina', 'otorgado_por'
    ).filter(activo=True).order_by('fecha_vencimiento')
    context = {
        'certificaciones':    certs,
        'total':              certs.count(),
        'vigentes':           sum(1 for c in certs if c.vigente),
        'vencidas':           sum(1 for c in certs if not c.vigente),
        'por_vencer':         certs.filter(
            fecha_vencimiento__gte=hoy,
            fecha_vencimiento__lte=hoy + timezone.timedelta(days=30)
        ).count(),
        'es_admin_o_tecnico': es_admin_o_tecnico(request.user),
    }
    return render(request, 'tpm/lista_certificaciones.html', context)


@login_required(login_url='login')
def crear_certificacion(request):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para otorgar certificaciones.')
        return redirect('lista_certificaciones')
    if request.method == 'POST':
        form = CertificacionForm(request.POST)
        if form.is_valid():
            cert = form.save(commit=False)
            cert.otorgado_por = request.user
            cert.activo       = True
            cert.save()
            messages.success(
                request,
                f'Certificación otorgada a {cert.usuario.username} para {cert.maquina.nombre}.'
            )
            return redirect('lista_certificaciones')
    else:
        form = CertificacionForm()
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
    if request.method == 'POST':
        form = CertificacionForm(request.POST, instance=cert)
        if form.is_valid():
            form.save()
            messages.success(request, 'Certificación actualizada correctamente.')
            return redirect('lista_certificaciones')
    else:
        form = CertificacionForm(instance=cert)
    return render(request, 'tpm/form_certificacion.html', {
        'form':   form,
        'cert':   cert,
        'titulo': f'Editar certificación — {cert.usuario.username}',
        'accion': 'Guardar cambios',
    })


@login_required(login_url='login')
def revocar_certificacion(request, pk):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para revocar certificaciones.')
        return redirect('lista_certificaciones')
    cert = get_object_or_404(CertificacionUsuario, pk=pk)
    if request.method == 'POST':
        cert.activo = False
        cert.save(update_fields=['activo'])
        messages.success(
            request,
            f'Certificación de {cert.usuario.username} para {cert.maquina.nombre} revocada.'
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
    return render(request, 'tpm/detalle_incidente.html', {'incidente': incidente})


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
    alertas = Alerta.objects.select_related('maquina').filter(resuelta=False)
    context = {
        'alertas':            alertas,
        'total':              alertas.count(),
        'criticas':           alertas.filter(severidad='CRITICA').count(),
        'advertencias':       alertas.filter(severidad='ADVERTENCIA').count(),
        'es_admin_o_tecnico': es_admin_o_tecnico(request.user),
    }
    return render(request, 'tpm/lista_alertas.html', context)


@login_required(login_url='login')
def resolver_alerta(request, pk):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para resolver alertas.')
        return redirect('lista_alertas')
    alerta = get_object_or_404(Alerta, pk=pk)
    if request.method == 'POST':
        alerta.resolver(request.user)
        messages.success(request, 'Alerta resuelta correctamente.')
        return redirect('lista_alertas')
    return redirect('lista_alertas')