from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('',                                  views.dashboard_tpm,          name='dashboard_tpm'),
    # Inspecciones
    path('inspecciones/',                                        views.lista_inspecciones,  name='lista_inspecciones'),
    path('inspecciones/<int:pk>/',                               views.detalle_inspeccion,  name='detalle_inspeccion'),
    path('inspecciones/<int:inspeccion_pk>/hallazgos/crear/',    views.agregar_hallazgo,    name='agregar_hallazgo'),
    # Hallazgos
    path('hallazgos/<int:pk>/editar/',                           views.editar_hallazgo,     name='editar_hallazgo'),
    path('hallazgos/<int:pk>/resolver/',                         views.resolver_hallazgo,   name='resolver_hallazgo'),
    path('hallazgos/<int:pk>/eliminar/',                         views.eliminar_hallazgo,   name='eliminar_hallazgo'),
    # Ítems de checklist (catálogo por fabricante+modelo)
    path('checklist-items/',                       views.lista_items_checklist,  name='lista_items_checklist'),
    path('checklist-items/crear/',                 views.crear_item_checklist,   name='crear_item_checklist'),
    path('checklist-items/<int:pk>/editar/',       views.editar_item_checklist,  name='editar_item_checklist'),
    path('checklist-items/<int:pk>/eliminar/',     views.eliminar_item_checklist, name='eliminar_item_checklist'),
    # Certificaciones
    path('certificaciones/',                  views.lista_certificaciones,  name='lista_certificaciones'),
    path('certificaciones/crear/',            views.crear_certificacion,    name='crear_certificacion'),
    path('certificaciones/<int:pk>/editar/',  views.editar_certificacion,   name='editar_certificacion'),
    path('certificaciones/<int:pk>/revocar/', views.revocar_certificacion,  name='revocar_certificacion'),
    # Incidentes
    path('incidentes/',                       views.lista_incidentes,       name='lista_incidentes'),
    path('incidentes/crear/',                 views.crear_incidente,        name='crear_incidente'),
    path('incidentes/<int:pk>/',              views.detalle_incidente,      name='detalle_incidente'),
    path('incidentes/<int:pk>/editar/',       views.editar_incidente,       name='editar_incidente'),
    # OEE
    path('oee/',                              views.lista_oee,              name='lista_oee'),
    path('oee/calcular/',                     views.calcular_oee,           name='calcular_oee'),
    # Alertas
    path('alertas/',                          views.lista_alertas,          name='lista_alertas'),
    path('alertas/<int:pk>/resolver/',        views.resolver_alerta,        name='resolver_alerta'),
]