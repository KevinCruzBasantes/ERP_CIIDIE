from django.contrib import messages
from django.shortcuts import redirect

from usuarios.permisos import es_estudiante

RUTAS_EXACTAS_PERMITIDAS = {'/', '/ingresar/', '/logout/', '/dashboard/', '/registro/'}
PREFIJOS_PERMITIDOS = ('/reservas/', '/media/', '/static/')


class RestriccionEstudianteMiddleware:
    """El estudiante solo puede usar el módulo de Reservas (incluye Órdenes de
    trabajo, que vive bajo /reservas/ordenes/) y su panel principal. El resto
    de módulos (Máquinas, Mantenimiento, TPM, Inventario, Usuarios, admin de
    Django) queda fuera aunque se escriba la URL directamente — ocultar el
    link del menú no era suficiente, esas vistas solo tenían @login_required."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated and es_estudiante(user):
            path = request.path
            permitido = path in RUTAS_EXACTAS_PERMITIDAS or path.startswith(PREFIJOS_PERMITIDOS)
            if not permitido:
                messages.error(request, 'Tu perfil de estudiante no tiene acceso a esa sección.')
                return redirect('dashboard_general')
        return self.get_response(request)
