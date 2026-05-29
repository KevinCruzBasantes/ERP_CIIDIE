from django.contrib import admin
from .models import Maquina


@admin.register(Maquina)
class MaquinaAdmin(admin.ModelAdmin):

    list_display = (
        'codigo',
        'nombre',
        'estado',
        'ubicacion',
    )

    list_filter = (
        'estado',
    )

    search_fields = (
        'codigo',
        'nombre',
    )