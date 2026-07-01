from usuarios.permisos import (
    es_admin as _es_admin,
    es_admin_o_tecnico as _es_admin_o_tecnico,
    es_operador as _es_operador,
)


def roles_usuario(request):
    """Expone nav_es_admin / nav_es_admin_o_tecnico / nav_es_operador a TODOS los
    templates (vía base.html), usando las mismas funciones de usuarios.permisos que
    ya usan las vistas (usuarios/maquinas/mantenimiento/reservas/tpm/inventario),
    para que el menú lateral nunca pueda divergir de la lógica de permisos real."""
    user = request.user
    es_admin = False
    es_admin_o_tecnico = False
    es_operador = False
    if user.is_authenticated:
        es_admin = _es_admin(user)
        es_admin_o_tecnico = _es_admin_o_tecnico(user)
        es_operador = _es_operador(user)
    return {
        'nav_es_admin': es_admin,
        'nav_es_admin_o_tecnico': es_admin_o_tecnico,
        'nav_es_operador': es_operador,
    }
