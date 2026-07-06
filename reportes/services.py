import io

from django.core.files.base import ContentFile
from django.db.models import Avg, F
from django.http import HttpResponse
from django.utils import timezone
from django.utils import timezone as tz
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

from .models import ReporteGenerado


# ─────────────────────────────────────────────────────────────────────────────
# Formateadores None-safe — para renderizar celdas sin reventar con FKs
# en NULL (SET_NULL) ni campos opcionales vacíos.
# ─────────────────────────────────────────────────────────────────────────────

def fmt_usuario(u):
    """Nombre completo (o username) de un Usuario, o '—' si el FK quedó en NULL."""
    if not u:
        return '—'
    return u.get_full_name() or u.username


def fmt_fecha(d):
    """DateField → 'dd/mm/aaaa' o '—'."""
    return d.strftime('%d/%m/%Y') if d else '—'


def fmt_fecha_hora(dt):
    """DateTimeField → 'dd/mm/aaaa HH:MM' en hora local, o '—'."""
    return tz.localtime(dt).strftime('%d/%m/%Y %H:%M') if dt else '—'


def si_no(v):
    return 'Sí' if v else 'No'


def fmt_num(x):
    """Decimal/int → float para la celda, o '—' si es None."""
    return float(x) if x is not None else '—'


def fmt_texto(t):
    """Texto opcional → el texto o '—' si está vacío."""
    return t if t else '—'


# ─────────────────────────────────────────────────────────────────────────────
# Construcción del workbook
# ─────────────────────────────────────────────────────────────────────────────

def estilo_encabezado(ws, fila, columnas):
    """Aplica estilo de encabezado a una fila."""
    fill = PatternFill(start_color='1E2333', end_color='1E2333', fill_type='solid')
    font = Font(bold=True, color='E8A020', size=10)
    for col, texto in enumerate(columnas, 1):
        cell = ws.cell(row=fila, column=col, value=texto)
        cell.font = font
        cell.fill = fill
        cell.alignment = Alignment(horizontal='center', vertical='center')


def escribir_hoja(wb, titulo, encabezados, filas, ancho=18):
    """Agrega una hoja al workbook con encabezado estilado y filas ya formateadas.

    Reutiliza la hoja inicial vacía del Workbook en la primera llamada para
    no dejar una pestaña "Sheet" huérfana en workbooks multi-hoja.
    """
    if wb.active and wb.active.max_row == 1 and wb.active.max_column == 1 \
            and wb.active.cell(row=1, column=1).value is None:
        ws = wb.active
        ws.title = titulo
    else:
        ws = wb.create_sheet(title=titulo)

    estilo_encabezado(ws, 1, encabezados)
    for i, fila in enumerate(filas, 2):
        for col, valor in enumerate(fila, 1):
            ws.cell(row=i, column=col, value=valor)

    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = ancho
    return ws


def generar_reporte_excel(request, *, tipo, nombre_base, hojas,
                          fecha_inicio=None, fecha_fin=None, observaciones=''):
    """Genera el workbook, lo guarda en el historial y lo devuelve como descarga.

    hojas: lista de tuplas (titulo, encabezados, filas) o
           (titulo, encabezados, filas, ancho).

    El workbook se serializa UNA sola vez: los mismos bytes van al FileField
    (re-descarga desde el historial) y al cuerpo de la respuesta.
    """
    wb = openpyxl.Workbook()
    for hoja in hojas:
        titulo, encabezados, filas = hoja[0], hoja[1], hoja[2]
        ancho = hoja[3] if len(hoja) > 3 else 18
        escribir_hoja(wb, titulo, encabezados, filas, ancho)

    buffer = io.BytesIO()
    wb.save(buffer)
    datos = buffer.getvalue()

    nombre = f"{nombre_base}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    reporte = ReporteGenerado(
        tipo=tipo,
        generado_por=request.user,
        fecha_inicio_periodo=fecha_inicio or timezone.now().date(),
        fecha_fin_periodo=fecha_fin or timezone.now().date(),
        observaciones=observaciones,
    )
    reporte.archivo.save(nombre, ContentFile(datos), save=True)

    response = HttpResponse(
        datos,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{nombre}"'
    return response


# ─────────────────────────────────────────────────────────────────────────────
# Consultas agregadas — fuente de datos del reporte RESUMEN (resumen ejecutivo)
# ─────────────────────────────────────────────────────────────────────────────

class ReporteService:

    @staticmethod
    def maquinas_mas_utilizadas(limite=10):
        from maquinas.models import Maquina
        return (Maquina.objects.exclude(estado='BAJA')
                .order_by('-horas_acumuladas')[:limite])

    @staticmethod
    def materiales_stock_bajo():
        from inventario.models import Material
        return (Material.objects.filter(activo=True,
                                        stock_actual__lte=F('stock_minimo'))
                .order_by('nombre'))

    @staticmethod
    def mantenimientos_pendientes():
        from mantenimiento.models import OrdenMantenimiento
        return (OrdenMantenimiento.objects
                .filter(activo=True, estado__in=['PROGRAMADA', 'EN_PROCESO'])
                .select_related('maquina', 'responsable_1')
                .order_by('fecha_programada'))

    @staticmethod
    def indicadores_tpm():
        from tpm.models import Alerta, CertificacionUsuario, Incidente, RegistroOEE

        hoy = timezone.now().date()

        oee_promedio = None
        oee_periodo = None
        ultimo = RegistroOEE.objects.filter(activo=True).order_by('-anio', '-mes').first()
        if ultimo:
            oee_periodo = f"{ultimo.mes:02d}/{ultimo.anio}"
            oee_promedio = (RegistroOEE.objects
                            .filter(activo=True, anio=ultimo.anio, mes=ultimo.mes)
                            .aggregate(prom=Avg('oee'))['prom'])

        alertas_activas = {
            severidad: Alerta.objects.filter(resuelta=False, severidad=severidad).count()
            for severidad, _ in Alerta.SEVERIDADES
        }

        certificaciones_por_vencer = (CertificacionUsuario.objects
                                      .filter(activo=True,
                                              fecha_vencimiento__gte=hoy,
                                              fecha_vencimiento__lte=hoy + timezone.timedelta(days=30))
                                      .select_related('usuario', 'maquina')
                                      .order_by('fecha_vencimiento'))

        incidentes_30d = Incidente.objects.filter(
            activo=True,
            fecha_ocurrencia__gte=timezone.now() - timezone.timedelta(days=30),
        ).count()

        return {
            'oee_promedio': oee_promedio,
            'oee_periodo': oee_periodo,
            'alertas_activas': alertas_activas,
            'certificaciones_por_vencer': certificaciones_por_vencer,
            'incidentes_30d': incidentes_30d,
        }
