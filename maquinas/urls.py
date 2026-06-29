# -*- coding: utf-8 -*-
from django.urls import path
from . import views

urlpatterns = [
    # Códigos de parada 
    path('codigos-parada/',                          views.lista_codigos_parada,    name='lista_codigos_parada'),
    path('codigos-parada/crear/',                    views.crear_codigo_parada,     name='crear_codigo_parada'),
    path('codigos-parada/<int:pk>/',                 views.detalle_codigo_parada,   name='detalle_codigo_parada'),
    path('codigos-parada/<int:pk>/editar/',          views.editar_codigo_parada,    name='editar_codigo_parada'),
    path('codigos-parada/<int:pk>/eliminar/',        views.eliminar_codigo_parada,  name='eliminar_codigo_parada'),

    # Piezas y transferencias
    path('transferencias/',                        views.lista_transferencias,  name='lista_transferencias'),
    path('piezas/<int:pk>/',                       views.detalle_pieza,         name='detalle_pieza'),
    path('piezas/<int:pk>/editar/',                views.editar_pieza,          name='editar_pieza'),
    path('piezas/<int:pk>/eliminar/',              views.eliminar_pieza,        name='eliminar_pieza'),
    path('piezas/<int:pk>/reasignar/',             views.reasignar_pieza,       name='reasignar_pieza'),
    path('piezas/<int:pieza_pk>/transferir/',      views.crear_transferencia,   name='crear_transferencia'),

    # Máquinas
    path('',                                      views.lista_maquinas,        name='lista_maquinas'),
    path('crear/',                                views.crear_maquina,         name='crear_maquina'),
    path('<int:pk>/',                             views.detalle_maquina,       name='detalle_maquina'),
    path('<int:pk>/editar/',                      views.editar_maquina,        name='editar_maquina'),
    path('<int:pk>/eliminar/',                    views.eliminar_maquina,      name='eliminar_maquina'),
    path('<int:pk>/estado/',                      views.cambiar_estado_maquina, name='cambiar_estado_maquina'),
    path('<int:maquina_pk>/piezas/crear/',        views.crear_pieza,           name='crear_pieza'),
    path('<int:maquina_pk>/ensambles/crear/',     views.crear_ensamble,        name='crear_ensamble'),
]