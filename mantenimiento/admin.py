from django.contrib import admin
from .models import Mantenimiento


@admin.register(Mantenimiento)
class MantenimientoAdmin(admin.ModelAdmin):

    list_display = (
        'maquina',
        'tipo',
        'estado',
        'prioridad',
        'fecha_programada',
        'responsable',
    )

    list_filter = (
        'tipo',
        'estado',
        'prioridad',
    )

    search_fields = (
        'maquina__nombre',
        'descripcion',
    )