from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('ingresar/', views.login_view, name='login'),
    path('registro/', views.registro_estudiante, name='registro_estudiante'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/admin/', views.dashboard_admin, name='dashboard_admin'),
    path('dashboard/tecnico/', views.dashboard_tecnico, name='dashboard_tecnico'),
    path('dashboard/operador/', views.dashboard_operador, name='dashboard_operador'),
    path('mi-horario/', views.mi_horario, name='mi_horario'),
    path('mi-horario/<int:pk>/eliminar/', views.eliminar_disponibilidad, name='eliminar_disponibilidad'),
    path('dashboard/', views.dashboard_general, name='dashboard_general'),
    path('inspeccion/', views.inspeccion_diaria, name='inspeccion_diaria'),
    path('usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    path('usuarios/<int:pk>/', views.detalle_usuario, name='detalle_usuario'),
    path('usuarios/<int:pk>/editar/', views.editar_usuario, name='editar_usuario'),
    path('usuarios/<int:pk>/estado/', views.cambiar_estado_usuario, name='cambiar_estado_usuario'),
    path('usuarios/<int:pk>/eliminar/', views.eliminar_usuario, name='eliminar_usuario'),
]