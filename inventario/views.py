import unicodedata

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import F
from .models import Material, ConsumoMaterial
from .forms import MaterialForm

from decimal import Decimal


def _normalizar_rol(nombre_rol):
    """Minúsculas y sin tildes, para que 'TECNICO' y 'Técnico' coincidan igual."""
    sin_tildes = unicodedata.normalize('NFKD', nombre_rol).encode('ascii', 'ignore').decode('ascii')
    return sin_tildes.lower()


def es_admin_o_tecnico(user):
    if user.is_superuser:
        return True
    if user.rol:
        rol = _normalizar_rol(user.rol.nombre)
        return any(r in rol for r in ['administrador', 'phd', 'tecnico', 'ingeniero'])
    return False


@login_required(login_url='login')
def lista_materiales(request):
    materiales = Material.objects.filter(activo=True)
    context = {
        'materiales':         materiales,
        'total':              materiales.count(),
        'stock_bajo':         materiales.filter(stock_actual__lte=F('stock_minimo')).count(),
        'mantenimiento':      materiales.filter(tipo='MANTENIMIENTO').count(),
        'produccion':         materiales.filter(tipo='PRODUCCION').count(),
        'ambos':              materiales.filter(tipo='AMBOS').count(),
        'es_admin_o_tecnico': es_admin_o_tecnico(request.user),
    }
    return render(request, 'inventario/lista_materiales.html', context)


@login_required(login_url='login')
def detalle_material(request, pk):
    material = get_object_or_404(Material, pk=pk)
    consumos = material.consumos.select_related('realizado_por', 'orden_trabajo').all()[:30]
    context = {
        'material':           material,
        'consumos':           consumos,
        'es_admin_o_tecnico': es_admin_o_tecnico(request.user),
    }
    return render(request, 'inventario/detalle_material.html', context)


@login_required(login_url='login')
def crear_material(request):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para crear materiales.')
        return redirect('lista_materiales')
    if request.method == 'POST':
        form = MaterialForm(request.POST)
        if form.is_valid():
            mat = form.save()
            messages.success(request, f'Material "{mat.nombre}" creado correctamente.')
            return redirect('detalle_material', pk=mat.pk)
    else:
        form = MaterialForm()
    return render(request, 'inventario/form_material.html', {
        'form':   form,
        'titulo': 'Nuevo material',
        'accion': 'Crear material',
    })


@login_required(login_url='login')
def editar_material(request, pk):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para editar materiales.')
        return redirect('detalle_material', pk=pk)
    material = get_object_or_404(Material, pk=pk)
    if request.method == 'POST':
        form = MaterialForm(request.POST, instance=material)
        if form.is_valid():
            form.save()
            messages.success(request, f'Material "{material.nombre}" actualizado.')
            return redirect('detalle_material', pk=pk)
    else:
        form = MaterialForm(instance=material)
    return render(request, 'inventario/form_material.html', {
        'form':     form,
        'material': material,
        'titulo':   f'Editar — {material.nombre}',
        'accion':   'Guardar cambios',
    })



@login_required(login_url='login')
def ajustar_stock(request, pk):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para ajustar stock.')
        return redirect('detalle_material', pk=pk)
    material = get_object_or_404(Material, pk=pk)
    if request.method == 'POST':
        operacion   = request.POST.get('operacion')
        observacion = request.POST.get('observacion', '')
        try:
            cantidad = Decimal(request.POST.get('cantidad', '0'))
            if cantidad <= 0:
                raise ValueError('La cantidad debe ser mayor que 0.')
            if operacion == 'entrada':
                material.stock_actual += cantidad
                material.save(update_fields=['stock_actual'])
                messages.success(request, f'Entrada de {cantidad} {material.unidad_medida} registrada. Stock: {material.stock_actual}.')
            elif operacion == 'salida':
                if material.stock_actual < cantidad:
                    raise ValueError(f'Stock insuficiente. Disponible: {material.stock_actual}.')
                ConsumoMaterial.objects.create(
                    material=material,
                    realizado_por=request.user,
                    cantidad=cantidad,
                    observacion=f'[Ajuste manual] {observacion}',
                )
                messages.success(request, f'Salida de {cantidad} {material.unidad_medida} registrada. Stock: {material.stock_actual}.')
            else:
                messages.error(request, 'Operación inválida.')
        except (ValueError, TypeError) as e:
            messages.error(request, str(e))
    return redirect('detalle_material', pk=pk)


@login_required(login_url='login')
def eliminar_material(request, pk):
    if not es_admin_o_tecnico(request.user):
        messages.error(request, 'No tienes permisos para eliminar materiales.')
        return redirect('detalle_material', pk=pk)
    material = get_object_or_404(Material, pk=pk)
    if request.method == 'POST':
        material.activo = False
        material.save(update_fields=['activo'])
        messages.success(request, f'Material "{material.nombre}" desactivado.')
        return redirect('lista_materiales')
    return render(request, 'inventario/confirmar_eliminar_material.html', {'material': material})