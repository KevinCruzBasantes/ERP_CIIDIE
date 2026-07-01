from django.db import migrations


def crear_rol_operador(apps, schema_editor):
    Rol = apps.get_model('usuarios', 'Rol')
    Rol.objects.get_or_create(nombre='OPERADOR')


def eliminar_rol_operador(apps, schema_editor):
    Rol = apps.get_model('usuarios', 'Rol')
    Rol.objects.filter(nombre='OPERADOR').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0003_alter_permiso_options_alter_rol_options_and_more'),
    ]

    operations = [
        migrations.RunPython(crear_rol_operador, eliminar_rol_operador),
    ]
