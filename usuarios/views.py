from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import F
from maquinas.models import Maquina
from mantenimiento.models import Mantenimiento, OrdenMantenimiento
from inventario.models import Material
from reservas.models import Reserva, OrdenTrabajo
from tpm.models import Alerta, InspeccionDiaria, ItemChecklistInspeccion, RespuestaChecklistInspeccion
from usuarios.permisos import es_admin, es_admin_o_tecnico, es_operador
from .models import Usuario, Rol, DisponibilidadOperador
from .forms import UsuarioCrearForm, UsuarioEditarForm, RegistroEstudianteForm, DisponibilidadOperadorForm


ROLES_LANDING = {
    'admin':      {'etiqueta': 'Administrador', 'campo_label': 'Usuario', 'placeholder': 'nombre de usuario'},
    'tecnico':    {'etiqueta': 'Técnico',        'campo_label': 'Usuario', 'placeholder': 'nombre de usuario'},
    'estudiante': {'etiqueta': 'Estudiante',     'campo_label': 'Cédula',  'placeholder': 'tu número de cédula'},
    'operador':   {'etiqueta': 'Operador',       'campo_label': 'Usuario', 'placeholder': 'nombre de usuario'},
}


def landing_view(request):
    if request.user.is_authenticated:
        return redirigir_por_rol(request.user)
    return render(request, 'usuarios/landing.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirigir_por_rol(request.user)
    rol = request.POST.get('rol') or request.GET.get('rol') or ''
    if request.method == 'POST':
        identificador = request.POST.get('username', '').strip()
        password = request.POST.get('password')
        # Admin/técnico/operador ingresan con su username; el estudiante con su cédula.
        # Si el identificador coincide con una cédula registrada, se resuelve
        # al username real antes de autenticar.
        usuario_por_cedula = Usuario.objects.filter(cedula=identificador).first()
        username = usuario_por_cedula.username if usuario_por_cedula else identificador
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.estado == 'ACTIVO':
                login(request, user)
                return redirigir_por_rol(user)
            else:
                messages.error(request, 'Tu cuenta está inactiva. Contacta al administrador.')
        else:
            messages.error(request, 'Usuario/cédula o contraseña incorrectos.')
    return render(request, 'usuarios/login.html', {
        'rol':      rol,
        'rol_info': ROLES_LANDING.get(rol),
    })


def registro_estudiante(request):
    if request.user.is_authenticated:
        return redirigir_por_rol(request.user)
    if request.method == 'POST':
        form = RegistroEstudianteForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Cuenta creada. Bienvenido, {user.get_full_name() or user.username}.')
            return redirect('dashboard_general')
    else:
        form = RegistroEstudianteForm()
    return render(request, 'usuarios/registro_estudiante.html', {'form': form})


def redirigir_por_rol(user):
    if es_admin(user):
        return redirect('dashboard_admin')
    elif es_admin_o_tecnico(user):
        return redirect('dashboard_tecnico')
    elif es_operador(user):
        return redirect('dashboard_operador')
    else:
        return redirect('dashboard_general')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required(login_url='login')
def dashboard_admin(request):
    hoy = timezone.now().date()
    context = {
        'total_maquinas': Maquina.objects.count(),
        'maquinas_operativas': Maquina.objects.filter(estado='OPERATIVA').count(),
        'maquinas_mantenimiento': Maquina.objects.filter(estado='MANTENIMIENTO').count(),
        'maquinas_fuera': Maquina.objects.filter(estado='BAJA').count(),
        'mant_programados': Mantenimiento.objects.filter(estado='PROGRAMADO').count(),
        'mant_vencidos': Mantenimiento.objects.filter(
            estado__in=['PROGRAMADO', 'EN_PROCESO'],
            fecha_programada__lt=hoy
        ).count(),
        'mant_proximos': Mantenimiento.objects.filter(
            estado='PROGRAMADO',
            fecha_programada__gte=hoy,
            fecha_programada__lte=hoy + timezone.timedelta(days=7)
        ).order_by('fecha_programada')[:5],
        'materiales_stock_bajo': Material.objects.filter(
            activo=True,
            stock_actual__lte=F('stock_minimo')
        ).count(),
        'reservas_pendientes': Reserva.objects.filter(estado='PENDIENTE').count(),
        'ordenes_en_proceso': OrdenTrabajo.objects.filter(estado='EN_PROCESO').count(),
        'om_abiertas': OrdenMantenimiento.objects.filter(
            activo=True, estado__in=['PROGRAMADA', 'EN_PROCESO']
        ).count(),
        'om_recientes': OrdenMantenimiento.objects.filter(
            activo=True, estado__in=['PROGRAMADA', 'EN_PROCESO']
        ).select_related('maquina').order_by('-fecha_creacion')[:5],
        'reservas_pendientes_lista': Reserva.objects.filter(
            estado='PENDIENTE'
        ).select_related('usuario', 'maquina').order_by('-fecha')[:5],
        'maquinas_en_mantenimiento': Maquina.objects.filter(
            estado='MANTENIMIENTO'
        ).select_related('responsable')[:6],
        'stock_bajo_lista': Material.objects.filter(
            activo=True, stock_actual__lte=F('stock_minimo')
        ).order_by('stock_actual')[:5],
        'alertas_activas': Alerta.objects.filter(resuelta=False).count(),
        'alertas_criticas': Alerta.objects.filter(resuelta=False, severidad='CRITICA').count(),
        'ultimas_alertas': Alerta.objects.filter(resuelta=False).select_related('maquina')[:5],
    }
    return render(request, 'usuarios/dashboard_admin.html', context)


@login_required(login_url='login')
def dashboard_tecnico(request):
    hoy = timezone.now().date()

    om_mias_en_proceso = OrdenMantenimiento.objects.filter(
        activo=True, estado='EN_PROCESO', responsable_1=request.user,
    ).select_related('maquina').order_by('-fecha_inicio')

    om_mias_programadas = OrdenMantenimiento.objects.filter(
        activo=True, estado='PROGRAMADA', responsable_1=request.user,
    ).select_related('maquina').order_by('fecha_programada')[:6]

    om_sin_asignar_lista = OrdenMantenimiento.objects.filter(
        activo=True, responsable_1__isnull=True,
        estado__in=['PROGRAMADA', 'EN_PROCESO'],
    ).select_related('maquina').order_by('fecha_programada')[:6]

    context = {
        'om_en_proceso_count':     om_mias_en_proceso.count(),
        'om_mias_abiertas':        OrdenMantenimiento.objects.filter(
                                       activo=True, responsable_1=request.user,
                                       estado__in=['PROGRAMADA', 'EN_PROCESO']
                                   ).count(),
        'om_sin_asignar':          OrdenMantenimiento.objects.filter(
                                       activo=True, responsable_1__isnull=True,
                                       estado__in=['PROGRAMADA', 'EN_PROCESO']
                                   ).count(),
        'alertas_activas':         Alerta.objects.filter(resuelta=False).count(),
        'om_mias_en_proceso':      om_mias_en_proceso,
        'om_mias_programadas':     om_mias_programadas,
        'om_sin_asignar_lista':    om_sin_asignar_lista,
        'alertas_lista':           Alerta.objects.filter(
                                       resuelta=False
                                   ).select_related('maquina').order_by('-generada_en')[:6],
        'inspecciones_hoy':        InspeccionDiaria.objects.filter(fecha=hoy).count(),
        'maquinas_sin_inspeccion': Maquina.objects.filter(
                                       estado='OPERATIVA'
                                   ).exclude(inspecciones_diarias__fecha=hoy).count(),
        'hoy': hoy,
    }
    return render(request, 'usuarios/dashboard_tecnico.html', context)


@login_required(login_url='login')
def dashboard_operador(request):
    hoy = timezone.now().date()
    en_una_semana = hoy + timezone.timedelta(days=7)
    reservas = Reserva.objects.filter(operador=request.user).select_related('usuario', 'maquina')
    context = {
        'reservas_hoy':      reservas.filter(fecha=hoy, estado__in=('APROBADA', 'EN_USO')).order_by('hora_inicio'),
        'proximas_reservas': reservas.filter(
            fecha__gt=hoy, fecha__lte=en_una_semana, estado__in=('PENDIENTE', 'APROBADA', 'EN_USO')
        ).order_by('fecha', 'hora_inicio'),
        'historial':         reservas.filter(estado='COMPLETADA').order_by('-fecha')[:10],
        'incidencias':       reservas.filter(estado='CANCELADA').order_by('-fecha')[:10],
    }
    return render(request, 'usuarios/dashboard_operador.html', context)


@login_required(login_url='login')
def mi_horario(request):
    if not es_operador(request.user):
        messages.error(request, 'Esta sección es solo para operadores.')
        return redirect('dashboard_general')
    if request.method == 'POST':
        form = DisponibilidadOperadorForm(request.POST)
        if form.is_valid():
            bloque = form.save(commit=False)
            bloque.operador = request.user
            bloque.save()
            messages.success(request, 'Horario agregado.')
            return redirect('mi_horario')
        else:
            messages.error(request, 'Revisa los datos del horario.')
    else:
        form = DisponibilidadOperadorForm()
    bloques = DisponibilidadOperador.objects.filter(operador=request.user)
    return render(request, 'usuarios/mi_horario.html', {'form': form, 'bloques': bloques})


@login_required(login_url='login')
def eliminar_disponibilidad(request, pk):
    bloque = get_object_or_404(DisponibilidadOperador, pk=pk, operador=request.user)
    if request.method == 'POST':
        bloque.delete()
        messages.success(request, 'Horario eliminado.')
    return redirect('mi_horario')


@login_required(login_url='login')
def dashboard_general(request):
    context = {
        'maquinas_operativas': Maquina.objects.filter(estado='OPERATIVA'),
        'mis_reservas': Reserva.objects.filter(
            usuario=request.user
        ).order_by('-fecha')[:5],
    }
    return render(request, 'usuarios/dashboard_general.html', context)


@login_required(login_url='login')
def inspeccion_diaria(request):
    hoy = timezone.now().date()
    maquinas = Maquina.objects.filter(estado='OPERATIVA')

    inspeccionadas_hoy = InspeccionDiaria.objects.filter(
        fecha=hoy
    ).select_related('maquina', 'inspector')

    inspeccionadas_ids = inspeccionadas_hoy.values_list('maquina_id', flat=True)
    pendientes = maquinas.exclude(id__in=inspeccionadas_ids)

    if request.method == 'POST':
        maquina_id = request.POST.get('maquina_id')
        if not maquina_id:
            messages.error(request, 'Debes seleccionar una máquina.')
            return redirect('inspeccion_diaria')
        maquina = get_object_or_404(Maquina, pk=maquina_id)

        if InspeccionDiaria.objects.filter(maquina=maquina, fecha=hoy).exists():
            messages.error(request, f'Ya existe una inspección para {maquina.nombre} hoy.')
            return redirect('inspeccion_diaria')

        inspeccion = InspeccionDiaria.objects.create(
            maquina=maquina,
            inspector=request.user,
            fecha=hoy,
            limpieza_area_ok=request.POST.get('limpieza_area_ok') == 'on',
            ruidos_anormales=request.POST.get('ruidos_anormales') == 'on',
            vibraciones_anormales=request.POST.get('vibraciones_anormales') == 'on',
            temperatura_normal=request.POST.get('temperatura_normal') == 'on',
            guardas_seguridad_ok=request.POST.get('guardas_seguridad_ok') == 'on',
            boton_emergencia_ok=request.POST.get('boton_emergencia_ok') == 'on',
            observaciones=request.POST.get('observaciones', ''),
        )

        # Ítems específicos del catálogo según fabricante+modelo de la máquina
        items_especificos = ItemChecklistInspeccion.objects.filter(
            fabricante=maquina.fabricante, modelo_maquina=maquina.modelo, activo=True
        )
        RespuestaChecklistInspeccion.objects.bulk_create([
            RespuestaChecklistInspeccion(
                inspeccion=inspeccion,
                item=item,
                ok=request.POST.get(f'item_{item.pk}') == 'on',
            )
            for item in items_especificos
        ])
        inspeccion.recalcular_aprobada()

        messages.success(request, f'Inspección de {maquina.nombre} registrada correctamente.')
        return redirect('inspeccion_diaria')

    # Ítems específicos por máquina pendiente, para mostrar el bloque correcto al elegirla
    pendientes_con_items = [
        {
            'maquina': m,
            'items': ItemChecklistInspeccion.objects.filter(
                fabricante=m.fabricante, modelo_maquina=m.modelo, activo=True
            ).order_by('orden', 'nombre'),
        }
        for m in pendientes
    ]

    context = {
        'maquinas': maquinas,
        'pendientes': pendientes,
        'pendientes_con_items': pendientes_con_items,
        'inspeccionadas_hoy': inspeccionadas_hoy,
        'hoy': hoy,
    }
    return render(request, 'usuarios/inspeccion_diaria.html', context)


@login_required(login_url='login')
def lista_usuarios(request):
    if not es_admin(request.user):
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('dashboard_admin')

    usuarios = Usuario.objects.select_related('rol').filter(is_superuser=False)
    context = {
        'usuarios': usuarios,
        'total': usuarios.count(),
        'activos': usuarios.filter(estado='ACTIVO').count(),
        'inactivos': usuarios.filter(estado='INACTIVO').count(),
        'suspendidos': usuarios.filter(estado='SUSPENDIDO').count(),
    }
    return render(request, 'usuarios/lista_usuarios.html', context)


@login_required(login_url='login')
def detalle_usuario(request, pk):
    if not es_admin(request.user):
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('dashboard_admin')

    usuario = get_object_or_404(Usuario, pk=pk, is_superuser=False)
    context = {'usuario': usuario}
    return render(request, 'usuarios/detalle_usuario.html', context)


@login_required(login_url='login')
def crear_usuario(request):
    if not es_admin(request.user):
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('lista_usuarios')

    if request.method == 'POST':
        form = UsuarioCrearForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            messages.success(request, f'Usuario "{usuario.username}" creado correctamente.')
            return redirect('detalle_usuario', pk=usuario.pk)
    else:
        form = UsuarioCrearForm()

    context = {
        'form': form,
        'titulo': 'Nuevo usuario',
        'accion': 'Crear usuario',
    }
    return render(request, 'usuarios/form_usuario.html', context)


@login_required(login_url='login')
def editar_usuario(request, pk):
    if not es_admin(request.user):
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('lista_usuarios')

    usuario = get_object_or_404(Usuario, pk=pk, is_superuser=False)

    if request.method == 'POST':
        form = UsuarioEditarForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, f'Usuario "{usuario.username}" actualizado correctamente.')
            return redirect('detalle_usuario', pk=usuario.pk)
    else:
        form = UsuarioEditarForm(instance=usuario)

    context = {
        'form': form,
        'usuario': usuario,
        'titulo': f'Editar — {usuario.get_full_name() or usuario.username}',
        'accion': 'Guardar cambios',
    }
    return render(request, 'usuarios/form_usuario.html', context)


@login_required(login_url='login')
def cambiar_estado_usuario(request, pk):
    if not es_admin(request.user):
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('lista_usuarios')

    usuario = get_object_or_404(Usuario, pk=pk, is_superuser=False)

    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado in ['ACTIVO', 'INACTIVO', 'SUSPENDIDO']:
            usuario.estado = nuevo_estado
            usuario.save()
            messages.success(
                request,
                f'Estado de "{usuario.username}" actualizado a {usuario.get_estado_display()}.'
            )
        else:
            messages.error(request, 'Estado inválido.')
    return redirect('detalle_usuario', pk=usuario.pk)


@login_required(login_url='login')
def eliminar_usuario(request, pk):
    if not es_admin(request.user):
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('lista_usuarios')

    usuario = get_object_or_404(Usuario, pk=pk, is_superuser=False)

    # Proteger: no puede eliminarse a sí mismo
    if usuario.pk == request.user.pk:
        messages.error(request, 'No puedes eliminar tu propia cuenta.')
        return redirect('detalle_usuario', pk=pk)

    if request.method == 'POST':
        nombre = usuario.get_full_name() or usuario.username
        usuario.delete()
        messages.success(request, f'Usuario "{nombre}" eliminado permanentemente.')
        return redirect('lista_usuarios')

    context = {'usuario': usuario}
    return render(request, 'usuarios/confirmar_eliminar_usuario.html', context)