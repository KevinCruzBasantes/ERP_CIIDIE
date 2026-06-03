from django.contrib import admin
from .models import Reserva, OrdenTrabajo, RegistroParada, BitacoraOperario


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'maquina', 'fecha', 'hora_inicio', 'hora_fin', 'estado', 'proposito']
    list_filter = ['estado', 'proposito', 'maquina']
    search_fields = ['usuario__username', 'usuario__first_name', 'maquina__nombre']
    ordering = ['-fecha', '-hora_inicio']


@admin.register(OrdenTrabajo)
class OrdenTrabajoAdmin(admin.ModelAdmin):
    list_display = ['id', 'reserva', 'estado', 'tiempo_planificado_min', 'tiempo_real_min', 'fecha_creacion']
    list_filter = ['estado']
    search_fields = ['reserva__usuario__username', 'descripcion']
    ordering = ['-fecha_creacion']


@admin.register(RegistroParada)
class RegistroParadaAdmin(admin.ModelAdmin):
    list_display = ['orden_trabajo', 'codigo_parada', 'hora_inicio', 'hora_fin', 'duracion_minutos']
    list_filter = ['codigo_parada__tipo']
    search_fields = ['descripcion_tecnica']


@admin.register(BitacoraOperario)
class BitacoraOperarioAdmin(admin.ModelAdmin):
    list_display = ['orden_trabajo', 'operario', 'fecha_registro', 'requiere_atencion']
    list_filter = ['requiere_atencion']
    search_fields = ['descripcion_trabajo', 'operario__username']