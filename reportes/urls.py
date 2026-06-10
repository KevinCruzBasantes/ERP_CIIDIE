from django.urls import path
from . import views

urlpatterns = [
    path('',                        views.lista_reportes,        name='lista_reportes'),
    path('generar/inventario/',     views.generar_inventario,    name='reporte_inventario'),
    path('generar/mantenimiento/',  views.generar_mantenimiento, name='reporte_mantenimiento'),
    path('generar/inspecciones/',   views.generar_inspecciones,  name='reporte_inspecciones'),
    path('generar/oee/',            views.generar_oee,           name='reporte_oee'),
    path('generar/reservas/',       views.generar_reservas,      name='reporte_reservas'),
    path('generar/pareto/',         views.generar_pareto,        name='reporte_pareto'),
]