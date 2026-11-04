import datetime
from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse_lazy
from django.utils import timezone

from .models import (
    Servicio, Usuario, Cita, CitaServicio, Pago,
    Disponibilidad, BloqueoHorario, ConfiguracionSistema,
    Categoria, Etiqueta,
)
from .forms import (
    RegistroClienteForm, LoginForm, FiltroReporteForm,
    CitaForm, EditarPerfilForm,
)


# ============================================================
# AUTENTICACIÓN
# ============================================================
def login_view(request):
    if request.user.is_authenticated:
        return redirect('reserva_paso1')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Bienvenido/a, {user.first_name or user.username}.')
            if user.rol in ['admin', 'profesional', 'estilista']:
                return redirect('admin_dashboard')
            return redirect('reserva_paso1')
        else:
            messages.error(request, 'Credenciales inválidas. Intenta nuevamente.')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})


def registro_view(request):
    if request.user.is_authenticated:
        return redirect('reserva_paso1')
    if request.method == 'POST':
        form = RegistroClienteForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'¡Cuenta creada! Bienvenido/a, {user.first_name}.')
            return redirect('reserva_paso1')
        else:
            messages.error(request, 'Revisa los datos del formulario.')
    else:
        form = RegistroClienteForm()
    return render(request, 'registro.html', {'form': form})


# ============================================================
# FLUJO DE RESERVA (multi-paso)
# ============================================================
def reserva_paso1_servicios(request):
    servicios = Servicio.objects.all().prefetch_related('etiquetas').select_related('categoria')
    return render(request, 'reserva_paso1_servicios.html', {'servicios': servicios})


def reserva_paso2_fecha(request, servicio_id):
    servicio = get_object_or_404(Servicio, pk=servicio_id)
    profesionales = Usuario.objects.filter(
        rol__in=['admin', 'profesional', 'estilista']
    ).order_by('first_name')
    return render(request, 'reserva_paso2_fecha.html', {
        'servicio': servicio,
        'profesionales': profesionales,
        'hoy': datetime.date.today().isoformat(),
    })


def reserva_paso3_horarios(request, servicio_id, empleado_id):
    servicio = get_object_or_404(Servicio, pk=servicio_id)
    empleado = get_object_or_404(Usuario, pk=empleado_id)
    fecha_str = request.GET.get('fecha', datetime.date.today().strftime('%Y-%m-%d'))

    try:
        fecha_obj = datetime.datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, 'Fecha inválida.')
        return redirect('reserva_paso1')

    slots_base = ['09:00', '10:00', '11:00', '12:30', '15:00', '16:30', '17:30', '18:30']
    citas_ese_dia = Cita.objects.filter(
        empleado=empleado,
        fecha_hora_cita__date=fecha_obj,
        estado__in=['pendiente', 'confirmada']
    ).values_list('fecha_hora_cita', flat=True)
    horas_ocupadas = {c.strftime('%H:%M') for c in citas_ese_dia}
    horarios_libres = [s for s in slots_base if s not in horas_ocupadas]

    return render(request, 'reserva_paso3_horarios.html', {
        'servicio': servicio,
        'empleado': empleado,
        'fecha': fecha_str,
        'horarios': horarios_libres,
    })


@login_required
def reserva_paso4_resumen(request):
    if request.method != 'POST':
        messages.warning(request, 'Por favor, completa la reserva desde el inicio.')
        return redirect('reserva_paso1')

    servicio_id = request.POST.get('servicio_id')
    empleado_id = request.POST.get('empleado_id')
    fecha_hora_str = request.POST.get('fecha_hora')

    servicio = get_object_or_404(Servicio, pk=servicio_id)
    empleado = get_object_or_404(Usuario, pk=empleado_id)

    config = ConfiguracionSistema.objects.first()

    # porcentaje SIEMPRE Decimal (corrige el TypeError Decimal * float)
    if config is not None:
        porcentaje = config.porcentaje_abono
    else:
        porcentaje = Decimal('50.00')

    monto_total = servicio.precio_serv  # ya es Decimal

    if config is not None and config.permite_monto_fijo:
        monto_abono = config.monto_fijo_abono
    else:
        monto_abono = monto_total * (porcentaje / Decimal('100'))

    # Redondeo al peso para evitar decimales largos en el template
    monto_abono = monto_abono.quantize(Decimal('1'))
    saldo_salon = (monto_total - monto_abono).quantize(Decimal('1'))

    return render(request, 'reserva_paso4_resumen.html', {
        'servicio': servicio,
        'empleado': empleado,
        'fecha_hora': fecha_hora_str,
        'monto_total': monto_total,
        'monto_abono': monto_abono,
        'saldo_salon': saldo_salon,
        'porcentaje': porcentaje,
    })


@login_required
def reserva_paso5_procesar_pago(request):
    if request.method != 'POST':
        messages.warning(request, 'Acción no permitida.')
        return redirect('reserva_paso1')

    servicio_id = request.POST.get('servicio_id')
    empleado_id = request.POST.get('empleado_id')
    fecha_hora_str = request.POST.get('fecha_hora')
    monto_abono_str = request.POST.get('monto_abono')
    metodo_pago = request.POST.get('metodo_pago', 'webpay')

    # Convertir monto a Decimal de forma segura
    try:
        monto_abono = Decimal(monto_abono_str)
    except (InvalidOperation, TypeError, ValueError):
        messages.error(request, 'El monto del abono es inválido.')
        return redirect('reserva_paso1')

    try:
        fecha_hora = datetime.datetime.strptime(fecha_hora_str, '%Y-%m-%d %H:%M')
    except (ValueError, TypeError):
        messages.error(request, 'Los datos de fecha/hora son inválidos.')
        return redirect('reserva_paso1')

    try:
        with transaction.atomic():
            cita_existente = Cita.objects.select_for_update().filter(
                empleado_id=empleado_id,
                fecha_hora_cita=fecha_hora,
                estado__in=['confirmada', 'pendiente']
            ).exists()

            if cita_existente:
                messages.error(request, 'El horario acaba de ser reservado por otra persona. Elige otro.')
                return redirect('reserva_paso1')

            nueva_cita = Cita.objects.create(
                cliente=request.user,
                empleado_id=empleado_id,
                fecha_hora_cita=fecha_hora,
                estado='confirmada',
                monto_abono=monto_abono,
                estado_abono='pagado',
            )
            servicio = Servicio.objects.get(pk=servicio_id)
            CitaServicio.objects.create(cita=nueva_cita, servicio=servicio)

            Pago.objects.create(
                cita=nueva_cita,
                cliente=request.user,
                monto=monto_abono,
                metodo_pago=metodo_pago,
                tipo_pago='abono',
                estado='completado',
                transaccion_id=f"PAY-{nueva_cita.id}-{int(datetime.datetime.now().timestamp())}",
            )

            despachar_notificacion_cita(nueva_cita)
            messages.success(request, '¡Reserva confirmada! Revisa tu correo.')
            return redirect('reserva_paso6_exito', cita_id=nueva_cita.id)
    except Exception as e:
        messages.error(request, f'Error al procesar la reserva: {e}')
        return redirect('reserva_paso1')


def reserva_paso6_exito(request, cita_id):
    cita = get_object_or_404(Cita, pk=cita_id)
    return render(request, 'reserva_paso6_exito.html', {'cita': cita})


def despachar_notificacion_cita(cita):
    intento_whatsapp_exitoso = False
    log_evento = {
        'timestamp': datetime.datetime.now().isoformat(),
        'canal': 'WhatsApp Business API',
        'estado': 'Fallido',
    }
    if not intento_whatsapp_exitoso:
        try:
            send_mail(
                subject=f"Confirmación de Reserva #{cita.id} - RG Beauty Spa",
                message=(
                    f"Hola {cita.cliente.first_name}, tu cita para el "
                    f"{cita.fecha_hora_cita.strftime('%d/%m/%Y a las %H:%M')} hrs ha sido confirmada."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[cita.cliente.email],
                fail_silently=False,
            )
            log_evento['canal_respaldo'] = 'Correo SMTP'
            log_evento['estado_respaldo'] = 'Enviado Exitosamente'
        except Exception as e:
            log_evento['error_smtp'] = str(e)

    cita.historial_notificaciones.append(log_evento)
    cita.save()


# ============================================================
# CRUD DE CITAS
# ============================================================
@login_required
def mis_citas(request):
    qs = (
        Cita.objects
        .filter(cliente=request.user)
        .select_related('empleado', 'cliente')
        .prefetch_related('servicios')
        .order_by('-fecha_hora_cita')
    )

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(empleado__first_name__icontains=q)
            | Q(empleado__last_name__icontains=q)
            | Q(servicios__nombre_serv__icontains=q)
            | Q(estado__icontains=q)
        ).distinct()

    estado = request.GET.get('estado', '').strip()
    if estado:
        qs = qs.filter(estado=estado)

    paginator = Paginator(qs, 5)
    page_obj = paginator.get_page(request.GET.get('page'))

    params = request.GET.copy()
    params.pop('page', None)
    querystring = params.urlencode()

    return render(request, 'mis_citas.html', {
        'page_obj': page_obj,
        'querystring': querystring,
        'q': q,
        'estado': estado,
        'estados': Cita.ESTADOS_CITA,
    })


@login_required
def detalle_cita(request, pk):
    cita = get_object_or_404(
        Cita.objects.select_related('cliente', 'empleado').prefetch_related('servicios'),
        pk=pk,
    )
    if cita.cliente != request.user and request.user.rol not in ['admin', 'profesional', 'estilista']:
        raise PermissionDenied('No tienes permiso para ver esta cita.')
    return render(request, 'detalle_cita.html', {'cita': cita})


@login_required
def editar_cita(request, pk):
    cita = get_object_or_404(Cita, pk=pk)
    if cita.cliente != request.user and request.user.rol != 'admin':
        raise PermissionDenied('Solo el dueño de la cita o la administradora pueden editarla.')

    if request.method == 'POST':
        form = CitaForm(request.POST, instance=cita, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cita actualizada correctamente.')
            return redirect('detalle_cita', pk=cita.pk)
        else:
            messages.error(request, 'Revisa los datos del formulario.')
    else:
        form = CitaForm(instance=cita, user=request.user)

    return render(request, 'editar_cita.html', {'form': form, 'cita': cita})


@login_required
def eliminar_cita(request, pk):
    cita = get_object_or_404(Cita, pk=pk)
    if cita.cliente != request.user and request.user.rol != 'admin':
        raise PermissionDenied('Solo el dueño de la cita o la administradora pueden eliminarla.')

    if request.method == 'POST':
        cita.delete()
        messages.success(request, f'Cita #{pk} eliminada correctamente.')
        return redirect('mis_citas')

    return render(request, 'confirmar_eliminar_cita.html', {'cita': cita})


@login_required
def crear_cita(request):
    if request.user.rol != 'admin':
        raise PermissionDenied('Solo la administradora puede crear citas manuales.')

    if request.method == 'POST':
        form = CitaForm(request.POST, user=request.user)
        if form.is_valid():
            cita = form.save()
            messages.success(request, f'Cita #{cita.id} creada correctamente.')
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'Revisa los datos del formulario.')
    else:
        form = CitaForm(user=request.user)

    return render(request, 'editar_cita.html', {'form': form, 'cita': None})


# ============================================================
# CUENTA DE USUARIO
# ============================================================
@login_required
def cuenta(request):
    total_citas = request.user.citas_cliente.count()
    return render(request, 'cuenta.html', {'total_citas': total_citas})


@login_required
def editar_perfil(request):
    if request.method == 'POST':
        form = EditarPerfilForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado correctamente.')
            return redirect('cuenta')
        else:
            messages.error(request, 'Revisa los datos del formulario.')
    else:
        form = EditarPerfilForm(instance=request.user)

    return render(request, 'editar_perfil.html', {'form': form})


class CambiarPasswordView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'cambiar_password.html'
    success_url = reverse_lazy('cuenta')

    def form_valid(self, form):
        messages.success(self.request, 'Tu contraseña fue actualizada correctamente.')
        return super().form_valid(form)


# ============================================================
# PANEL ADMINISTRADOR
# ============================================================
@login_required
def admin_dashboard(request):
    if request.user.rol not in ['admin', 'profesional', 'estilista']:
        raise PermissionDenied('No tienes acceso al panel de administración.')

    citas = (
        Cita.objects
        .select_related('cliente', 'empleado')
        .prefetch_related('servicios')
        .order_by('-fecha_hora_cita')[:50]
    )
    form_reporte = FiltroReporteForm()
    config = ConfiguracionSistema.objects.first()

    return render(request, 'admin_dashboard.html', {
        'citas': citas,
        'form_reporte': form_reporte,
        'config': config,
    })