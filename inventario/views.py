from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import F
from .models import Material, ConsumoMaterial


@login_required(login_url='login')
def lista_materiales(request):
    materiales = Material.objects.filter(activo=True)
    context = {
        'materiales': materiales,
        'total': materiales.count(),
        'stock_bajo': materiales.filter(stock_actual__lte=F('stock_minimo')).count(),
        'mantenimiento': materiales.filter(tipo='MANTENIMIENTO').count(),
        'produccion': materiales.filter(tipo='PRODUCCION').count(),
        'ambos': materiales.filter(tipo='AMBOS').count(),
    }
    return render(request, 'inventario/lista_materiales.html', context)


@login_required(login_url='login')
def detalle_material(request, pk):
    material = get_object_or_404(Material, pk=pk)
    consumos = material.consumos.select_related(
        'realizado_por', 'orden_trabajo'
    ).all()[:20]
    context = {
        'material': material,
        'consumos': consumos,
    }
    return render(request, 'inventario/detalle_material.html', context)