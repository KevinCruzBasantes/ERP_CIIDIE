from django.contrib import admin

from .models import (
    InspeccionTPM,
    IndicadorTPM,
    HallazgoTPM
)


admin.site.register(InspeccionTPM)
admin.site.register(IndicadorTPM)
admin.site.register(HallazgoTPM)