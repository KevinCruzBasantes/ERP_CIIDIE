import unicodedata


def _normalizar_rol(nombre_rol):
    """Minúsculas y sin tildes, para que 'TECNICO' y 'Técnico' coincidan igual."""
    sin_tildes = unicodedata.normalize('NFKD', nombre_rol).encode('ascii', 'ignore').decode('ascii')
    return sin_tildes.lower()


def roles_usuario(request):
    """Expone nav_es_admin / nav_es_admin_o_tecnico a TODOS los templates (vía base.html),
    usando la misma normalización que ya usan las vistas (usuarios/maquinas/mantenimiento/
    reservas/tpm/inventario), para que el menú lateral no dependa de una comparación de
    roles distinta (y más frágil) definida solo en el template."""
    user = request.user
    es_admin = False
    es_admin_o_tecnico = False
    if user.is_authenticated:
        if user.is_superuser:
            es_admin = True
            es_admin_o_tecnico = True
        elif user.rol:
            rol = _normalizar_rol(user.rol.nombre)
            es_admin = 'administrador' in rol or 'phd' in rol
            es_admin_o_tecnico = es_admin or any(r in rol for r in ['tecnico', 'ingeniero'])
    return {
        'nav_es_admin': es_admin,
        'nav_es_admin_o_tecnico': es_admin_o_tecnico,
    }
