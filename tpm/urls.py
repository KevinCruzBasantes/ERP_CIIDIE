from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_tpm, name='dashboard_tpm'),
    path('inspecciones/', views.lista_inspecciones, name='lista_inspecciones'),
    path('inspecciones/<int:pk>/', views.detalle_inspeccion, name='detalle_inspeccion'),
    path('certificaciones/', views.lista_certificaciones, name='lista_certificaciones'),
    path('incidentes/', views.lista_incidentes, name='lista_incidentes'),
    path('oee/', views.lista_oee, name='lista_oee'),
]