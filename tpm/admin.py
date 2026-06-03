from django.contrib import admin
from .models import (
    CertificacionUsuario,
    InspeccionDiaria,
    HallazgoInspeccion,
    RegistroOEE,
    Incidente,
    Alerta,
)

admin.site.register(CertificacionUsuario)
admin.site.register(InspeccionDiaria)
admin.site.register(HallazgoInspeccion)
admin.site.register(RegistroOEE)
admin.site.register(Incidente)
admin.site.register(Alerta)