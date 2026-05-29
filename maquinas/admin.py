from django.contrib import admin
from .models import Maquina, Pieza, TransferenciaPieza


admin.site.register(Maquina)
admin.site.register(Pieza)
admin.site.register(TransferenciaPieza)