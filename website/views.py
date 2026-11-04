from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages


# Create your views here.
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from .models import (Servicio, Usuario, Cita, CitaServicio, Pago,
Disponibilidad, BloqueoHorario, ConfiguracionSistema)
from .forms import RegistroClienteForm, LoginForm, FiltroReporteForm, CitaForm, EditarPerfilForm
from decimal import Decimal
from django.utils import timezone
#imports para la cuenta del usuario/cliente 
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse_lazy, reverse
from .forms import CitaForm, EditarPerfilForm


def home_view(request):
    return render(request, 'home.html')   


def login_view(request): 
    if request.method == 'POST': 
        form = LoginForm(request, data=request.POST) 
        if form.is_valid(): 
            user = form.get_user() 
            login(request, user) 
            if user.rol in ['admin', 'profesional']: 
                return redirect('admin_dashboard') 
            return redirect('reserva_paso1') 
    else: 
        form = LoginForm() 
    return render(request, 'login.html', {'form': form}) 


def logout_view(request): 
    logout(request) 
    return redirect('login') 

 
def registro_view(request): 
    if request.method == 'POST': 
        form = RegistroClienteForm(request.POST) 
        if form.is_valid(): 
            user = form.save() 
            login(request, user) 
            return redirect('reserva_paso1') 
    else: 
        form = RegistroClienteForm() 
    return render(request, 'registro.html', {'form': form}) 

# --------------------------------------------------
# FUNCIÓN REUTILIZABLE (para no repetir lógica)
# --------------------------------------------------
def calcular_horarios_disponibles(servicio, empleado, fecha_obj):
    """Devuelve la lista de horarios libres para un empleado, servicio y fecha."""
    dias_semana = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo']
    nombre_dia = dias_semana[fecha_obj.weekday()]
    
    disponibilidad = Disponibilidad.objects.filter(
        empleado=empleado, 
        dia_semana=nombre_dia
    ).first()
    
    horarios_libres = []
    
    if disponibilidad:
        hora_inicio_dia = datetime.datetime.combine(fecha_obj, disponibilidad.hora_inicio)
        hora_fin_dia = datetime.datetime.combine(fecha_obj, disponibilidad.hora_fin)
        
        hay_bloqueo = BloqueoHorario.objects.filter(
            empleado=empleado,
            fecha_inicio__lte=fecha_obj,
            fecha_fin__gte=fecha_obj
        ).exists()
        
        if not hay_bloqueo:
            citas_existentes = Cita.objects.filter(
                empleado=empleado,
                estado__in=['pendiente', 'confirmada']
            )
            
            rangos_ocupados = []
            for cita in citas_existentes:
                cita_inicio_local = timezone.localtime(cita.fecha_hora_cita).replace(tzinfo=None)
                if cita_inicio_local.date() == fecha_obj:
                    servicios_de_cita = cita.citaservicio_set.all()
                    if servicios_de_cita.exists():
                        duracion_cita = sum([cs.servicio.duracion_minutos for cs in servicios_de_cita])
                    else:
                        duracion_cita = 60
                    
                    cita_fin_local = cita_inicio_local + datetime.timedelta(minutes=duracion_cita)
                    rangos_ocupados.append((cita_inicio_local, cita_fin_local))
            
            duracion_servicio = datetime.timedelta(minutes=servicio.duracion_minutos)
            intervalo = datetime.timedelta(minutes=30)
            hora_candidata = hora_inicio_dia
            
            while hora_candidata + duracion_servicio <= hora_fin_dia:
                fin_candidato = hora_candidata + duracion_servicio
                solapa = False
                
                for inicio_ocupado, fin_ocupado in rangos_ocupados:
                    if hora_candidata < fin_ocupado and fin_candidato > inicio_ocupado:
                        solapa = True
                        break
                
                if not solapa:
                    horarios_libres.append(hora_candidata.strftime('%H:%M'))
                
                hora_candidata += intervalo
    
    return horarios_libres


# --------------------------------------------------
# VISTA DEL PASO 3 (usa la función)
# --------------------------------------------------


# --------------------------------------------------
# API PARA QUE EL PASO 2 VERIFIQUE ANTES DE AVANZAR
# --------------------------------------------------
@login_required
def api_verificar_disponibilidad(request, servicio_id, empleado_id):
    """Devuelve JSON diciendo si hay horarios disponibles o no."""
    servicio = get_object_or_404(Servicio, pk=servicio_id)
    empleado = get_object_or_404(Usuario, pk=empleado_id)
    fecha_str = request.GET.get('fecha')
    
    if not fecha_str:
        return JsonResponse({'disponible': False, 'count': 0, 'error': 'Fecha no proporcionada'})
    
    try:
        fecha_obj = datetime.datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'disponible': False, 'count': 0, 'error': 'Formato de fecha inválido'})
    
    hoy = timezone.localdate()
    if fecha_obj <= hoy:
        return JsonResponse({'disponible': False, 'count': 0, 'error': 'Fecha no permitida'})
    
    horarios = calcular_horarios_disponibles(servicio, empleado, fecha_obj)
    return JsonResponse({'disponible': len(horarios) > 0, 'count': len(horarios)})

@login_required
def reserva_paso1_servicios(request): 
    servicios = Servicio.objects.all() 
    return render(request, 'reserva_paso1_servicios.html', {'servicios': servicios}) 

@login_required
def reserva_paso2_fecha(request, servicio_id): 
    servicio = get_object_or_404(Servicio, pk=servicio_id) 
    profesionales = Usuario.objects.filter(rol__in=['admin', 'profesional']) 
    
    # Calcular fecha mínima: mañana
    hoy = timezone.localdate()
    fecha_minima = hoy + datetime.timedelta(days=1)
    
    return render(request, 'reserva_paso2_fecha.html', {
        'servicio': servicio, 
        'profesionales': profesionales,
        'fecha_minima': fecha_minima.strftime('%Y-%m-%d')
    })

@login_required
def reserva_paso3_horarios(request, servicio_id, empleado_id): 
    servicio = get_object_or_404(Servicio, pk=servicio_id) 
    empleado = get_object_or_404(Usuario, pk=empleado_id) 
    
    # 1. Validar que la fecha venga en la URL
    fecha_str = request.GET.get('fecha')
    if not fecha_str:
        messages.error(request, 'Debes seleccionar una fecha antes de ver los horarios.')
        return redirect('reserva_paso2', servicio_id=servicio_id)
    
    # 2. Convertir la fecha a objeto date
    fecha_obj = datetime.datetime.strptime(fecha_str, '%Y-%m-%d').date()
    
    # 3. Validación de seguridad: bloquear fechas pasadas o de hoy
    hoy = timezone.localdate()
    if fecha_obj <= hoy:
        messages.error(request, 'Debes seleccionar una fecha a partir de mañana.')
        return redirect('reserva_paso2', servicio_id=servicio_id)
    
    # 4. Calcular horarios usando la función reutilizable
    horarios_libres = calcular_horarios_disponibles(servicio, empleado, fecha_obj)

    # 5. Renderizar el template
    return render(request, 'reserva_paso3_horarios.html', {
        'servicio': servicio, 
        'empleado': empleado, 
        'fecha': fecha_str, 
        'horarios': horarios_libres
    })

@login_required 
def reserva_paso4_resumen(request): 
    servicio_id = request.POST.get('servicio_id') 
    empleado_id = request.POST.get('empleado_id') 
    fecha_hora_str = request.POST.get('fecha_hora') 
     
    # VALIDACIÓN: Si no hay fecha o es "None", devolver al paso 3
    if not fecha_hora_str or fecha_hora_str == 'None':
        messages.error(request, 'Debes seleccionar un horario válido antes de continuar.')
        return redirect('reserva_paso3', servicio_id=servicio_id, empleado_id=empleado_id)

    servicio = get_object_or_404(Servicio, pk=servicio_id) 
    empleado = get_object_or_404(Usuario, pk=empleado_id) 
     
    config = ConfiguracionSistema.objects.first() 
    porcentaje = config.porcentaje_abono if config else Decimal('50.00') 
     
    monto_total = servicio.precio_serv 
    if config and config.permite_monto_fijo: 
        monto_abono = config.monto_fijo_abono 
    else: 
        monto_abono = (monto_total * (porcentaje / Decimal('100'))) 
         
    saldo_salon = monto_total - monto_abono 
     
    return render(request, 'reserva_paso4_resumen.html', { 
        'servicio': servicio, 'empleado': empleado, 'fecha_hora': fecha_hora_str, 
        'monto_total': monto_total, 'monto_abono': monto_abono, 
        'saldo_salon': saldo_salon, 'porcentaje': porcentaje 
    }) 

@login_required 
def reserva_paso5_procesar_pago(request): 
    if request.method == 'POST': 
        servicio_id = request.POST.get('servicio_id') 
        empleado_id = request.POST.get('empleado_id') 
        fecha_hora_str = request.POST.get('fecha_hora')
        monto_abono_raw = request.POST.get('monto_abono', '0') 
        metodo_pago = request.POST.get('metodo_pago', 'webpay') 
         
        # VALIDACIÓN: Evitar que el sistema intente procesar "None"
        if not fecha_hora_str or fecha_hora_str == 'None':
            messages.error(request, 'Hubo un problema con la fecha. Por favor, selecciona tu horario nuevamente.')
            return redirect('reserva_paso3', servicio_id=servicio_id, empleado_id=empleado_id)

        # Conversión segura de monto (reemplazo de coma por punto por locale es-cl)
        monto_abono = Decimal(monto_abono_raw.replace(',', '.'))

        servicio = get_object_or_404(Servicio, pk=servicio_id)
        empleado = get_object_or_404(Usuario, pk=empleado_id)
         
        fecha_hora_naive = datetime.datetime.strptime(fecha_hora_str, '%Y-%m-%d %H:%M') 
        fecha_hora = timezone.make_aware(fecha_hora_naive, timezone.get_current_timezone())
        fecha_obj = fecha_hora.date()
        
        # VALIDACIÓN EXTRA: Verificar que el horario sigue libre
        horarios_actuales = calcular_horarios_disponibles(servicio, empleado, fecha_obj)
        hora_solicitada = fecha_hora.strftime('%H:%M')
        
        if hora_solicitada not in horarios_actuales:
            messages.error(request, 'Lo sentimos, el horario que seleccionaste ya fue reservado por otra persona. Por favor elige otro.')
            url = reverse('reserva_paso3', kwargs={'servicio_id': servicio_id, 'empleado_id': empleado_id})
            return redirect(f'{url}?fecha={fecha_obj.isoformat()}')
         
        try: 
            with transaction.atomic(): 
                cita_existente = Cita.objects.select_for_update().filter( 
                    empleado_id=empleado_id, fecha_hora_cita=fecha_hora, estado__in=['confirmada', 'pendiente'] 
                ).exists() 
                 
                if cita_existente: 
                    messages.error(request, 'El horario acaba de ser reservado por otra persona. Por favor elige otro.')
                    url = reverse('reserva_paso3', kwargs={'servicio_id': servicio_id, 'empleado_id': empleado_id})
                    return redirect(f'{url}?fecha={fecha_obj.isoformat()}')

                # Recalcular monto por seguridad (evitar que el usuario lo manipule en el HTML)
                config = ConfiguracionSistema.objects.first()
                porcentaje = config.porcentaje_abono if config else Decimal('50.00')
                monto_total = servicio.precio_serv
                if config and config.permite_monto_fijo:
                    monto_abono_calculado = config.monto_fijo_abono
                else:
                    monto_abono_calculado = (monto_total * (porcentaje / Decimal('100')))
                
                # Usamos el calculado por seguridad, o el del POST si confías en el front (mejor usar el calculado)
                monto_abono = monto_abono_calculado
                 
                nueva_cita = Cita.objects.create( 
                    cliente=request.user, empleado_id=empleado_id, fecha_hora_cita=fecha_hora, 
                    estado='confirmada', monto_abono=monto_abono, estado_abono='pagado' 
                ) 
                CitaServicio.objects.create(cita=nueva_cita, servicio=servicio) 
                 
                Pago.objects.create( 
                    cita=nueva_cita, cliente=request.user, monto=monto_abono, 
                    metodo_pago=metodo_pago, tipo_pago='abono', estado='completado', 
                    transaccion_id=f"PAY-{nueva_cita.id}-{int(datetime.datetime.now().timestamp())}" 
                ) 
                 
                despachar_notificacion_cita(nueva_cita) 
                messages.success(request, '¡Tu reserva ha sido confirmada con éxito!')
                return redirect('reserva_paso6_exito', cita_id=nueva_cita.id) 
                 
        except Exception as e: 
            messages.error(request, f'Ocurrió un error al procesar tu pago: {str(e)}')
            return redirect('reserva_paso1')
@login_required
def reserva_paso6_exito(request, cita_id): 
    cita = get_object_or_404(Cita, pk=cita_id) 
    return render(request, 'reserva_paso6_exito.html', {'cita': cita}) 


def despachar_notificacion_cita(cita): 
    intento_whatsapp_exitoso = False 
    log_evento = {'timestamp': datetime.datetime.now().isoformat(), 'canal': 'WhatsApp Business API', 'estado': 'Fallido'} 
     
    if not intento_whatsapp_exitoso: 
        try: 
            send_mail( 
                subject=f"Confirmación de Reserva #{cita.id} - RG Beauty Spa", 
                message=f"Hola {cita.cliente.first_name}, tu cita para el {cita.fecha_hora_cita.strftime('%d/%m/%Y a las %H:%M')} hrs ha sido confirmada.", 
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
 
@login_required
def admin_dashboard(request):
    # Permitir solo a los roles autorizados
    if not (request.user.is_superuser or request.user.rol in ['admin', 'profesional', 'estilista']):
        messages.error(request, 'No tienes permiso para acceder al panel de administración.')
        return redirect('reserva_paso1')

    # Traer citas optimizadas para evitar el problema N+1
    citas = (
        Cita.objects
        .select_related('cliente', 'empleado')
        .prefetch_related('servicios')
        .order_by('-fecha_hora_cita')
    )
    
    form_reporte = FiltroReporteForm()
    config = ConfiguracionSistema.objects.first()

    # Calcular algunas estadísticas simples para mostrar en las tarjetas
    total_citas = citas.count()
    citas_confirmadas = citas.filter(estado='confirmada').count()
    citas_canceladas = citas.filter(estado='cancelada').count()

    return render(request, 'admin_dashboard.html', {
        'citas': citas,
        'form_reporte': form_reporte,
        'config': config,
        'total_citas': total_citas,
        'citas_confirmadas': citas_confirmadas,
        'citas_canceladas': citas_canceladas,
    })


@login_required
def admin_cambiar_estado(request, pk):
    """Vista que permite a la dueña cambiar el estado de una cita desde el panel web."""
    if not (request.user.is_superuser or request.user.rol in ['admin', 'profesional', 'estilista']):
        raise PermissionDenied('No tienes permiso para realizar esta acción.')

    cita = get_object_or_404(Cita, pk=pk)
    
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        
        # Validar que el estado enviado sea uno de los permitidos en el modelo
        estados_validos = [opcion[0] for opcion in Cita.ESTADOS_CITA]
        
        if nuevo_estado in estados_validos:
            cita.estado = nuevo_estado
            cita.save()
            messages.success(request, f'Cita #{cita.id} actualizada a: {cita.get_estado_display()}.')
        else:
            messages.error(request, 'El estado enviado no es válido.')
            
    return redirect('admin_dashboard')

def registro(request):
    if request.method == 'POST':
        form = RegistroClienteForm(request.POST)
        if form.is_valid():
            Usuario = form.save()
            login(request, Usuario)
            messages.success(request, f'Bienvenido, {Usuario.username}.')
            return redirect('home')
    else:
        form = RegistroClienteForm()
    return render(request, 'registro.html', {'form': form})

# MIS CITAS (listado, edición, eliminación del cliente)

@login_required
def mis_citas(request):
    qs = (
        Cita.objects
        .filter(cliente=request.user)
        .select_related('empleado')
        .prefetch_related('servicios')
        .order_by('-fecha_hora_cita')
    )

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(empleado__first_name__icontains=q)
            | Q(empleado__last_name__icontains=q)
            | Q(servicios__nombre_serv__icontains=q)
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

# detalle de citas, editar y eliminar citas del cliente
@login_required
def detalle_cita(request, pk):
    cita = get_object_or_404(
        Cita.objects.select_related('empleado').prefetch_related('servicios'),
        pk=pk
    )
    if cita.cliente != request.user:
        raise PermissionDenied('No tienes permiso para ver esta cita.')
    return render(request, 'detalle_cita.html', {'cita': cita})


@login_required
def editar_cita(request, pk):
    cita = get_object_or_404(Cita, pk=pk)
    
    if cita.cliente != request.user:
        raise PermissionDenied('Solo puedes editar tus propias citas.')

    # Si la cita ya está en un estado final, no se puede editar
    if cita.estado in ['cancelada', 'no_asistio', 'completada']:
        messages.error(request, 'No puedes modificar una cita que ya fue cancelada, completada o marcada como inasistencia.')
        return redirect('detalle_cita', pk=cita.pk)

    if request.method == 'POST':
        form = CitaForm(request.POST, instance=cita)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cita actualizada correctamente.')
            return redirect('detalle_cita', pk=cita.pk)
        else:
            messages.error(request, 'Revisa los datos del formulario.')
    else:
        form = CitaForm(instance=cita)

    return render(request, 'editar_cita.html', {'form': form, 'cita': cita})

@login_required
def eliminar_cita(request, pk):
    cita = get_object_or_404(Cita, pk=pk)
    
    if cita.cliente != request.user:
        raise PermissionDenied('Solo puedes cancelar tus propias citas.')

    if request.method == 'POST':
        cita.estado = 'cancelada'
        cita.save()
        messages.success(request, f'Cita #{pk} cancelada correctamente.')
        return redirect('mis_citas')

    return render(request, 'confirmar_eliminar_cita.html', {'cita': cita})

# Mi cuenta (perfil, edición, cambio de contraseña)

@login_required
def cuenta(request):
    total_citas = Cita.objects.filter(cliente=request.user).count()
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

#cambiar contraseña de cliente
class CambiarPasswordView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'cambiar_password.html'
    success_url = reverse_lazy('cuenta')

    def form_valid(self, form):
        messages.success(self.request, 'Tu contraseña fue actualizada correctamente.')
        return super().form_valid(form)