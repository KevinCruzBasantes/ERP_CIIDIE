from django.contrib import admin
from .models import Mantenimiento, OrdenMantenimiento, BitacoraMantenimiento


@admin.register(Mantenimiento)
class MantenimientoAdmin(admin.ModelAdmin):
    list_display   = ('maquina', 'tipo', 'estado', 'prioridad', 'fecha_programada', 'responsable')
    list_filter    = ('tipo', 'estado', 'prioridad')
    search_fields  = ('maquina__nombre', 'descripcion')


@admin.register(OrdenMantenimiento)
class OrdenMantenimientoAdmin(admin.ModelAdmin):
    list_display   = ('__str__', 'maquina', 'tipo', 'origen', 'estado', 'prioridad', 'fecha_programada', 'responsable_1')
    list_filter    = ('tipo', 'origen', 'estado', 'prioridad', 'afecta_seguridad', 'para_produccion')
    search_fields  = ('maquina__nombre', 'titulo')
    raw_id_fields  = ('responsable_1', 'responsable_2', 'responsable_3', 'creado_por', 'autorizado_por')


@admin.register(BitacoraMantenimiento)
class BitacoraMantenimientoAdmin(admin.ModelAdmin):
    list_display  = ('maquina', 'orden', 'tecnico', 'fecha_registro', 'requiere_atencion')
    list_filter   = ('requiere_atencion',)
    search_fields = ('maquina__nombre', 'descripcion')