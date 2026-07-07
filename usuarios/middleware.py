from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils import timezone

from usuarios.permisos import es_estudiante

RUTAS_EXACTAS_PERMITIDAS = {'/', '/ingresar/', '/logout/', '/dashboard/', '/registro/'}
PREFIJOS_PERMITIDOS = ('/reservas/', '/media/', '/static/')


class CierreSesionPorInactividadMiddleware:
    """Cierra la sesión automáticamente tras N minutos sin actividad
    (SESION_INACTIVIDAD_MINUTOS en settings). Cada petición autenticada
    refresca el contador; pasado el límite se hace logout y se redirige al
    login con un aviso. Complementa a SESSION_EXPIRE_AT_BROWSER_CLOSE, que
    solo actúa cuando el usuario cierra el navegador."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.limite_segundos = getattr(settings, 'SESION_INACTIVIDAD_MINUTOS', 30) * 60

    def __call__(self, request):
        if request.user.is_authenticated:
            ahora = timezone.now().timestamp()
            ultima = request.session.get('ultima_actividad')
            if ultima is not None and (ahora - ultima) > self.limite_segundos:
                logout(request)
                messages.info(request, 'Tu sesión se cerró por inactividad. Vuelve a ingresar.')
                return redirect('login')
            request.session['ultima_actividad'] = ahora
        return self.get_response(request)


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
