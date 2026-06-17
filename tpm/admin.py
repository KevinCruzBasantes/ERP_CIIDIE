from django.contrib import admin
from .models import (
    CertificacionUsuario,
    InspeccionDiaria,
    HallazgoInspeccion,
    RegistroOEE,
    Incidente,
    Alerta,
    ItemChecklistInspeccion,
    RespuestaChecklistInspeccion,
)

admin.site.register(CertificacionUsuario)
admin.site.register(InspeccionDiaria)
admin.site.register(HallazgoInspeccion)
admin.site.register(RegistroOEE)
admin.site.register(Incidente)
admin.site.register(Alerta)


@admin.register(ItemChecklistInspeccion)
class ItemChecklistInspeccionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'modelo_maquina', 'fabricante', 'es_critico', 'orden', 'activo')
    list_filter = ('es_critico', 'activo', 'fabricante', 'modelo_maquina')
    search_fields = ('nombre', 'fabricante', 'modelo_maquina')


admin.site.register(RespuestaChecklistInspeccion)