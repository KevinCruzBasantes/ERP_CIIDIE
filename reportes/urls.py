from django.urls import path
from . import views

urlpatterns = [
    path('',                        views.lista_reportes,       name='lista_reportes'),
    path('generar/resumen/',        views.generar_resumen,      name='reporte_resumen'),
    path('generar/mantenimiento/',  views.generar_mantenimiento, name='reporte_mantenimiento'),
    path('generar/produccion/',     views.generar_produccion,   name='reporte_produccion'),
    path('generar/inventario/',     views.generar_inventario,   name='reporte_inventario'),
    path('generar/seguridad/',      views.generar_seguridad,    name='reporte_seguridad'),
    path('generar/backup/',         views.generar_backup,       name='reporte_backup'),
]
