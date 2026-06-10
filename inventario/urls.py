from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_materiales, name='lista_materiales'),
    path('<int:pk>/', views.detalle_material, name='detalle_material'),
]