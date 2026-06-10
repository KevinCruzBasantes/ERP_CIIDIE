from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import (
    CertificacionUsuario, InspeccionDiaria,
    RegistroOEE, Incidente, Alerta
)
from .forms import CertificacionForm


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
        'incidentes_criticos': Incidente.objects.filter(severidad='CRITICA').count(),
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
        messages.success(request, f'Alerta resuelta correctamente.')
        return redirect('lista_alertas')
    return redirect('lista_alertas')