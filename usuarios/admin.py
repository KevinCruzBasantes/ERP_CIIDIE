from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario, Rol, Permiso


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)


@admin.register(Permiso)
class PermisoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):

    model = Usuario

    list_display = (
        'username',
        'first_name',
        'last_name',
        'email',
        'cedula',
        'rol',
        'estado',
        'is_staff',
    )

    list_filter = (
        'rol',
        'estado',
        'is_staff',
        'is_superuser',
    )

    fieldsets = UserAdmin.fieldsets + (
        (
            'Información adicional',
            {
                'fields': (
                    'cedula',
                    'telefono',
                    'rol',
                    'permisos_personalizados',
                    'estado',
                )
            }
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            'Información adicional',
            {
                'fields': (
                    'cedula',
                    'telefono',
                    'rol',
                    'estado',
                )
            },
        ),
    )

    search_fields = (
        'username',
        'first_name',
        'last_name',
        'cedula',
        'email',
    )