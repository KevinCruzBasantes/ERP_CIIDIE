from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_maquinas, name='lista_maquinas'),
    path('<int:pk>/', views.detalle_maquina, name='detalle_maquina'),
    path('crear/', views.crear_maquina, name='crear_maquina'),
    path('<int:pk>/editar/', views.editar_maquina, name='editar_maquina'),
    path('<int:pk>/eliminar/', views.eliminar_maquina, name='eliminar_maquina'),
    path('<int:pk>/estado/', views.cambiar_estado_maquina, name='cambiar_estado_maquina'),
]