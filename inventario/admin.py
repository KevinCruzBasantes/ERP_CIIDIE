from django.contrib import admin
from .models import Material, ConsumoMaterial


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):

    list_display = (
        'codigo',
        'nombre',
        'tipo',
        'stock_actual',
        'stock_minimo',
        'activo'
    )

    list_filter = (
        'tipo',
        'activo'
    )

    search_fields = (
        'codigo',
        'nombre'
    )


@admin.register(ConsumoMaterial)
class ConsumoMaterialAdmin(admin.ModelAdmin):

    list_display = (
        'material',
        'cantidad',
        'fecha'
    )

    search_fields = (
        'material__nombre',
    )