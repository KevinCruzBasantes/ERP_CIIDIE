from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Reserva, OrdenTrabajo


@login_required(login_url='login')
def lista_reservas(request):
    reservas = Reserva.objects.select_related(
        'usuario', 'maquina', 'autorizador'
    ).all()
    context = {
        'reservas': reservas,
        'total': reservas.count(),
        'pendientes': reservas.filter(estado='PENDIENTE').count(),
        'aprobadas': reservas.filter(estado='APROBADA').count(),
        'en_uso': reservas.filter(estado='EN_USO').count(),
        'completadas': reservas.filter(estado='COMPLETADA').count(),
    }
    return render(request, 'reservas/lista_reservas.html', context)


@login_required(login_url='login')
def detalle_reserva(request, pk):
    reserva = get_object_or_404(
        Reserva.objects.select_related('usuario', 'maquina', 'autorizador'),
        pk=pk
    )
    orden = getattr(reserva, 'orden_trabajo', None)
    context = {
        'reserva': reserva,
        'orden': orden,
    }
    return render(request, 'reservas/detalle_reserva.html', context)


@login_required(login_url='login')
def lista_ordenes(request):
    ordenes = OrdenTrabajo.objects.select_related(
        'reserva__usuario', 'reserva__maquina'
    ).all()
    context = {
        'ordenes': ordenes,
        'total': ordenes.count(),
        'abiertas': ordenes.filter(estado='ABIERTA').count(),
        'en_proceso': ordenes.filter(estado='EN_PROCESO').count(),
        'finalizadas': ordenes.filter(estado='FINALIZADA').count(),
    }
    return render(request, 'reservas/lista_ordenes.html', context)


@login_required(login_url='login')
def detalle_orden(request, pk):
    orden = get_object_or_404(
        OrdenTrabajo.objects.select_related(
            'reserva__usuario', 'reserva__maquina'
        ).prefetch_related('paradas__codigo_parada', 'entradas_bitacora__operario'),
        pk=pk
    )
    context = {
        'orden': orden,
        'paradas': orden.paradas.all(),
        'bitacora': orden.entradas_bitacora.all(),
        'consumos': orden.consumos_material.select_related('material').all(),
    }
    return render(request, 'reservas/detalle_orden.html', context)