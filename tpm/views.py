from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import (
    CertificacionUsuario, InspeccionDiaria,
    RegistroOEE, Incidente, Alerta
)


@login_required(login_url='login')
def dashboard_tpm(request):
    hoy = timezone.now().date()
    context = {
        'total_inspecciones': InspeccionDiaria.objects.count(),
        'inspecciones_hoy': InspeccionDiaria.objects.filter(fecha=hoy).count(),
        'inspecciones_fallidas': InspeccionDiaria.objects.filter(aprobada=False).count(),
        'certificaciones_vencidas': CertificacionUsuario.objects.filter(
            fecha_vencimiento__lt=hoy
        ).count(),
        'certificaciones_por_vencer': CertificacionUsuario.objects.filter(
            fecha_vencimiento__gte=hoy,
            fecha_vencimiento__lte=hoy + timezone.timedelta(days=30)
        ).count(),
        'incidentes_criticos': Incidente.objects.filter(severidad='CRITICA').count(),
        'alertas_activas': Alerta.objects.filter(resuelta=False).count(),
        'alertas_criticas': Alerta.objects.filter(resuelta=False, severidad='CRITICA').count(),
        'ultimas_alertas': Alerta.objects.filter(resuelta=False).select_related('maquina')[:8],
        'ultimas_inspecciones': InspeccionDiaria.objects.select_related(
            'maquina', 'inspector'
        ).order_by('-fecha')[:5],
        'ultimo_oee': RegistroOEE.objects.select_related('maquina').first(),
    }
    return render(request, 'tpm/dashboard_tpm.html', context)


@login_required(login_url='login')
def lista_inspecciones(request):
    inspecciones = InspeccionDiaria.objects.select_related('maquina', 'inspector').all()
    context = {
        'inspecciones': inspecciones,
        'total': inspecciones.count(),
        'aprobadas': inspecciones.filter(aprobada=True).count(),
        'fallidas': inspecciones.filter(aprobada=False).count(),
    }
    return render(request, 'tpm/lista_inspecciones.html', context)


@login_required(login_url='login')
def detalle_inspeccion(request, pk):
    inspeccion = get_object_or_404(
        InspeccionDiaria.objects.select_related('maquina', 'inspector'),
        pk=pk
    )
    context = {
        'inspeccion': inspeccion,
        'hallazgos': inspeccion.hallazgos.all(),
    }
    return render(request, 'tpm/detalle_inspeccion.html', context)


@login_required(login_url='login')
def lista_certificaciones(request):
    hoy = timezone.now().date()
    certs = CertificacionUsuario.objects.select_related(
        'usuario', 'maquina', 'otorgado_por'
    ).all()
    context = {
        'certificaciones': certs,
        'total': certs.count(),
        'vigentes': sum(1 for c in certs if c.vigente),
        'vencidas': sum(1 for c in certs if not c.vigente),
        'por_vencer': certs.filter(
            fecha_vencimiento__gte=hoy,
            fecha_vencimiento__lte=hoy + timezone.timedelta(days=30)
        ).count(),
    }
    return render(request, 'tpm/lista_certificaciones.html', context)


@login_required(login_url='login')
def lista_incidentes(request):
    incidentes = Incidente.objects.select_related('maquina', 'reportado_por').all()
    context = {
        'incidentes': incidentes,
        'total': incidentes.count(),
        'criticos': incidentes.filter(severidad='CRITICA').count(),
        'requieren_mto': incidentes.filter(requiere_mantenimiento=True).count(),
    }
    return render(request, 'tpm/lista_incidentes.html', context)


@login_required(login_url='login')
def lista_oee(request):
    registros = RegistroOEE.objects.select_related('maquina').all()
    context = {
        'registros': registros,
        'total': registros.count(),
    }
    return render(request, 'tpm/lista_oee.html', context)