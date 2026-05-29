from django.contrib import admin

from .models import ReporteGenerado


@admin.register(ReporteGenerado)
class ReporteGeneradoAdmin(admin.ModelAdmin):

    list_display = (
        'tipo',
        'generado_por',
        'fecha_generacion',
    )

    list_filter = (
        'tipo',
    )