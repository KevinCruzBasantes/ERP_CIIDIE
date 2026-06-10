from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from .models import Maquina
from .forms import MaquinaForm


def es_admin(user):
    if user.is_superuser:
        return True
    if user.rol:
        rol = user.rol.nombre.lower()
        return 'administrador' in rol or 'phd' in rol
    return False


@login_required(login_url='login')
def lista_maquinas(request):
    maquinas = Maquina.objects.select_related('responsable').all()
    context = {
        'maquinas': maquinas,
        'total': maquinas.count(),
        'operativas': maquinas.filter(estado='OPERATIVA').count(),
        'en_mantenimiento': maquinas.filter(estado='MANTENIMIENTO').count(),
        'fuera_servicio': maquinas.filter(estado='FUERA_SERVICIO').count(),
        'es_admin': es_admin(request.user),
    }
    return render(request, 'maquinas/lista_maquinas.html', context)


@login_required(login_url='login')
def detalle_maquina(request, pk):
    maquina = get_object_or_404(Maquina, pk=pk)
    ensambles = maquina.piezas.filter(
        es_ensamble=True, activo=True
    ).prefetch_related('piezas_hijas')
    context = {
        'maquina': maquina,
        'ensambles': ensambles,
        'es_admin': es_admin(request.user),
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

    context = {
        'form': form,
        'titulo': 'Nueva máquina',
        'accion': 'Crear',
    }
    return render(request, 'maquinas/form_maquina.html', context)


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

    context = {
        'form': form,
        'maquina': maquina,
        'titulo': f'Editar — {maquina.nombre}',
        'accion': 'Guardar cambios',
    }
    return render(request, 'maquinas/form_maquina.html', context)


@login_required(login_url='login')
def eliminar_maquina(request, pk):
    if not es_admin(request.user):
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('detalle_maquina', pk=pk)

    maquina = get_object_or_404(Maquina, pk=pk)

    if request.method == 'POST':
        maquina.estado = 'FUERA_SERVICIO'
        maquina.save()
        messages.success(request, f'Máquina "{maquina.nombre}" desactivada del sistema.')
        return redirect('lista_maquinas')

    context = {'maquina': maquina}
    return render(request, 'maquinas/confirmar_eliminar_maquina.html', context)


@login_required(login_url='login')
def cambiar_estado_maquina(request, pk):
    if not es_admin(request.user):
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('detalle_maquina', pk=pk)

    maquina = get_object_or_404(Maquina, pk=pk)

    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado in ['OPERATIVA', 'MANTENIMIENTO', 'FUERA_SERVICIO']:
            maquina.estado = nuevo_estado
            maquina.save()
            messages.success(request, f'Estado de "{maquina.nombre}" actualizado a {maquina.get_estado_display()}.')
        return redirect('detalle_maquina', pk=maquina.pk)

    return redirect('detalle_maquina', pk=pk)