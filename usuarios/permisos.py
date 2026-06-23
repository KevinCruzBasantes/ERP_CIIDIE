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
