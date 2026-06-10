from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Mantenimiento, PlanMantenimiento
from .forms import MantenimientoForm


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