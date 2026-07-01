from django.urls import path
from . import views

urlpatterns = [
    # Reservas
    path('',                                views.lista_reservas,         name='lista_reservas'),
    path('crear/',                          views.crear_reserva,          name='crear_reserva'),
    path('horarios-ocupados/',              views.horarios_ocupados,      name='horarios_ocupados'),
    path('operadores-certificados/',        views.operadores_certificados, name='operadores_certificados'),
    path('disponibilidad-operadores/',      views.disponibilidad_operadores_maquina, name='disponibilidad_operadores_maquina'),
    path('<int:pk>/',                       views.detalle_reserva,        name='detalle_reserva'),
    path('<int:pk>/editar/',                views.editar_reserva,         name='editar_reserva'),
    path('<int:pk>/estado/',                views.cambiar_estado_reserva, name='cambiar_estado_reserva'),
    path('<int:pk>/cancelar/',              views.cancelar_reserva,       name='cancelar_reserva'),
    # Órdenes de trabajo
    path('ordenes/',                        views.lista_ordenes,          name='lista_ordenes'),
    path('ordenes/crear/<int:reserva_pk>/', views.crear_orden,            name='crear_orden'),
    path('ordenes/<int:pk>/',               views.detalle_orden,          name='detalle_orden'),
    path('ordenes/<int:pk>/cerrar/',        views.cerrar_orden,           name='cerrar_orden'),
    path('ordenes/<int:orden_pk>/parada/',  views.agregar_parada,         name='agregar_parada'),
    path('ordenes/<int:orden_pk>/bitacora/',views.agregar_bitacora,       name='agregar_bitacora'),
    path('ordenes/<int:orden_pk>/consumo/', views.registrar_consumo,      name='registrar_consumo'),
]