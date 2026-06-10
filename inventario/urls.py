from django.urls import path
from . import views

urlpatterns = [
    path('',                   views.lista_materiales,  name='lista_materiales'),
    path('crear/',             views.crear_material,    name='crear_material'),
    path('<int:pk>/',          views.detalle_material,  name='detalle_material'),
    path('<int:pk>/editar/',   views.editar_material,   name='editar_material'),
    path('<int:pk>/stock/',    views.ajustar_stock,     name='ajustar_stock'),
    path('<int:pk>/eliminar/', views.eliminar_material, name='eliminar_material'),
]