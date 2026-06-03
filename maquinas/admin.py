from django.contrib import admin
from .models import Maquina, Pieza, TransferenciaPieza, CodigoParada


@admin.register(Maquina)
class MaquinaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'fabricante', 'modelo', 'estado', 'ubicacion')
    list_filter = ('estado', 'fabricante')
    search_fields = ('codigo', 'nombre', 'numero_serie')


@admin.register(Pieza)
class PiezaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'maquina', 'ensamble', 'es_ensamble', 'numero_parte', 'stock_repuestos')
    list_filter = ('es_ensamble', 'maquina')
    search_fields = ('nombre', 'numero_parte', 'nombre_original')


@admin.register(TransferenciaPieza)
class TransferenciaPiezaAdmin(admin.ModelAdmin):
    list_display = ('pieza', 'maquina_origen', 'maquina_destino', 'autorizado_por', 'fecha')
    list_filter = ('maquina_origen', 'maquina_destino')
    search_fields = ('pieza__nombre', 'motivo')


@admin.register(CodigoParada)
class CodigoParadaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'modelo_maquina', 'fabricante', 'tipo', 'categoria', 'subsistema')
    list_filter = ('tipo', 'categoria', 'fabricante', 'modelo_maquina')
    search_fields = ('codigo', 'subsistema')