from django.contrib import admin
from .models import Reserva, OrdenTrabajo


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):

    list_display = (
        'usuario',
        'maquina',
        'fecha',
        'hora_inicio',
        'hora_fin',
        'estado'
    )

    list_filter = (
        'estado',
        'fecha'
    )

    search_fields = (
        'usuario__username',
        'maquina__nombre'
    )


@admin.register(OrdenTrabajo)
class OrdenTrabajoAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'reserva',
        'estado',
        'tiempo_estimado_horas',
        'tiempo_real_horas'
    )

    list_filter = (
        'estado',
    )