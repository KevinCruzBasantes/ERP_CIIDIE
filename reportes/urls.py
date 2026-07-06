from django.urls import path
from . import views

urlpatterns = [
    path('',                          views.lista_reportes,                name='lista_reportes'),
    path('generar/inventario/',       views.generar_inventario,            name='reporte_inventario'),
    path('generar/mantenimiento/',    views.generar_mantenimiento,         name='reporte_mantenimiento'),
    path('generar/inspecciones/',     views.generar_inspecciones,          name='reporte_inspecciones'),
    path('generar/oee/',              views.generar_oee,                   name='reporte_oee'),
    path('generar/reservas/',         views.generar_reservas,              name='reporte_reservas'),
    path('generar/pareto/',           views.generar_pareto,                name='reporte_pareto'),
    path('generar/ordenes/',          views.generar_ordenes_mantenimiento, name='reporte_ordenes'),
    path('generar/alertas/',          views.generar_alertas,               name='reporte_alertas'),
    path('generar/certificaciones/',  views.generar_certificaciones,       name='reporte_certificaciones'),
    path('generar/incidentes/',       views.generar_incidentes,            name='reporte_incidentes'),
    path('generar/consumos/',         views.generar_consumos,              name='reporte_consumos'),
    path('generar/piezas/',           views.generar_piezas,                name='reporte_piezas'),
    path('generar/bitacoras/',        views.generar_bitacoras,             name='reporte_bitacoras'),
    path('generar/resumen/',          views.generar_resumen,               name='reporte_resumen'),
]
