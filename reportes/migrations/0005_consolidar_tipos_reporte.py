from django.db import migrations, models

# Los 14 tipos antiguos se consolidan en 6 grupos temáticos.
# Mapeo de códigos viejos → nuevo grupo (los que conservan código no aparecen).
MAPEO_TIPOS = {
    'CONSUMO_MATERIALES': 'INVENTARIO',
    'PIEZAS': 'INVENTARIO',
    'ORDENES_MANTENIMIENTO': 'MANTENIMIENTO',
    'BITACORAS': 'MANTENIMIENTO',
    'RESERVAS': 'PRODUCCION',
    'TPM_OEE': 'PRODUCCION',
    'TPM_PARETO': 'PRODUCCION',
    'TPM_INSPECCIONES': 'PRODUCCION',
    'ALERTAS': 'SEGURIDAD',
    'CERTIFICACIONES': 'SEGURIDAD',
    'INCIDENTES': 'SEGURIDAD',
}


def consolidar_tipos(apps, schema_editor):
    ReporteGenerado = apps.get_model('reportes', 'ReporteGenerado')
    for viejo, nuevo in MAPEO_TIPOS.items():
        ReporteGenerado.objects.filter(tipo=viejo).update(tipo=nuevo)


class Migration(migrations.Migration):

    dependencies = [
        ('reportes', '0004_alter_reportegenerado_tipo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reportegenerado',
            name='tipo',
            field=models.CharField(choices=[
                ('RESUMEN', 'Resumen ejecutivo'),
                ('MANTENIMIENTO', 'Mantenimiento'),
                ('PRODUCCION', 'Producción y uso'),
                ('INVENTARIO', 'Inventario y piezas'),
                ('SEGURIDAD', 'Seguridad y personal'),
                ('BACKUP', 'Respaldo completo'),
            ], max_length=30),
        ),
        migrations.RunPython(consolidar_tipos, migrations.RunPython.noop),
    ]
