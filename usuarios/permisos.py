import unicodedata


def _normalizar_rol(nombre_rol):
    """Minúsculas y sin tildes, para que 'TECNICO' y 'Técnico' coincidan igual."""
    sin_tildes = unicodedata.normalize('NFKD', nombre_rol).encode('ascii', 'ignore').decode('ascii')
    return sin_tildes.lower()


def es_admin(user):
    if user.is_superuser:
        return True
    if user.rol:
        rol = _normalizar_rol(user.rol.nombre)
        return 'administrador' in rol or 'phd' in rol
    return False


def es_admin_o_tecnico(user):
    if user.is_superuser:
        return True
    if user.rol:
        rol = _normalizar_rol(user.rol.nombre)
        return any(r in rol for r in ['administrador', 'phd', 'tecnico', 'ingeniero'])
    return False


def es_estudiante(user):
    if user.is_superuser:
        return False
    if user.rol:
        return 'estudiante' in _normalizar_rol(user.rol.nombre)
    return False


def es_operador(user):
    if user.is_superuser:
        return False
    if user.rol:
        return 'operador' in _normalizar_rol(user.rol.nombre)
    return False


def filtrar_usuarios_por_rol(queryset, criterio):
    """Filtra un queryset de Usuario con uno de los helpers de rol de este módulo
    (es_admin, es_admin_o_tecnico, ...). La comparación de roles es por substring
    sin tildes y no se puede expresar en SQL, así que se evalúa en Python —
    aceptable porque la tabla de usuarios es pequeña."""
    ids = [u.pk for u in queryset if criterio(u)]
    return queryset.filter(pk__in=ids)
