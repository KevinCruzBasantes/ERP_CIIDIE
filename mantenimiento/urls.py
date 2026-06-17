from django.urls import path
from . import views

urlpatterns = [
    # Registro de mantenimientos (historial/correctivos rápidos)
    path('',                       views.lista_mantenimientos,          name='lista_mantenimientos'),
    path('crear/',                 views.crear_mantenimiento,           name='crear_mantenimiento'),
    path('<int:pk>/',              views.detalle_mantenimiento,         name='detalle_mantenimiento'),
    path('<int:pk>/editar/',       views.editar_mantenimiento,          name='editar_mantenimiento'),
    path('<int:pk>/eliminar/',     views.eliminar_mantenimiento,        name='eliminar_mantenimiento'),
    path('<int:pk>/estado/',       views.cambiar_estado_mantenimiento,  name='cambiar_estado_mantenimiento'),
    # Planes de mantenimiento
    path('planes/',                views.lista_planes,                  name='lista_planes'),
    path('planes/crear/',          views.crear_plan,                    name='crear_plan'),
    path('planes/<int:pk>/',       views.detalle_plan,                  name='detalle_plan'),
    path('planes/<int:pk>/editar/', views.editar_plan,                  name='editar_plan'),
    path('planes/<int:pk>/eliminar/',            views.eliminar_plan,              name='eliminar_plan'),
    path('planes/<int:pk>/restaurar/',           views.restaurar_plan,             name='restaurar_plan'),
    path('planes/<int:pk>/eliminar-definitivo/', views.eliminar_plan_definitivo,   name='eliminar_plan_definitivo'),
    # Órdenes de mantenimiento (al estilo DANEC)
    path('ordenes/',                         views.lista_ordenes_mantenimiento,   name='lista_ordenes_mantenimiento'),
    path('ordenes/crear/',                   views.crear_orden_mantenimiento,     name='crear_orden_mantenimiento'),
    path('ordenes/<int:pk>/',                views.detalle_orden_mantenimiento,   name='detalle_orden_mantenimiento'),
    path('ordenes/<int:pk>/editar/',         views.editar_orden_mantenimiento,    name='editar_orden_mantenimiento'),
    path('ordenes/<int:pk>/estado/',         views.cambiar_estado_om,             name='cambiar_estado_om'),
    path('ordenes/<int:pk>/eliminar/',       views.eliminar_orden_mantenimiento,  name='eliminar_orden_mantenimiento'),
    path('ordenes/<int:om_pk>/bitacora/',    views.agregar_entrada_bitacora,      name='agregar_entrada_bitacora'),
    # Bitácora por máquina
    path('bitacora/<int:maquina_pk>/',       views.bitacora_maquina,              name='bitacora_maquina'),
]