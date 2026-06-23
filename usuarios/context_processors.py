from usuarios.permisos import es_admin as _es_admin, es_admin_o_tecnico as _es_admin_o_tecnico


def roles_usuario(request):
    """Expone nav_es_admin / nav_es_admin_o_tecnico a TODOS los templates (vía base.html),
    usando la misma función de usuarios.permisos que ya usan las vistas (usuarios/maquinas/
    mantenimiento/reservas/tpm/inventario), para que el menú lateral nunca pueda divergir
    de la lógica de permisos real."""
    user = request.user
    es_admin = False
    es_admin_o_tecnico = False
    if user.is_authenticated:
        es_admin = _es_admin(user)
        es_admin_o_tecnico = _es_admin_o_tecnico(user)
    return {
        'nav_es_admin': es_admin,
        'nav_es_admin_o_tecnico': es_admin_o_tecnico,
    }
