from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_reservas, name='lista_reservas'),
    path('<int:pk>/', views.detalle_reserva, name='detalle_reserva'),
    path('ordenes/', views.lista_ordenes, name='lista_ordenes'),
    path('ordenes/<int:pk>/', views.detalle_orden, name='detalle_orden'),
]