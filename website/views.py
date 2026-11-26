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
from django.db.models import Sum
from django.core.paginator import Paginator
from django.db.models.functions import TruncMonth
from django.db.models import Q, Count
from collections import defaultdict
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet



from .models import (
    Servicio, Usuario, Cita, CitaServicio, Pago, Disponibilidad, BloqueoHorario, ConfiguracionSistema
)

from .forms import (
    RegistroClienteForm, LoginForm, FiltroReporteForm, CitaForm, EditarPerfilForm, ServicioForm, ProfesionalForm, DisponibilidadForm, BloqueoForm, ConfiguracionForm
)

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
    
    # Traemos a los profesionales que ofrecen el servicio
    profesionales = Usuario.objects.filter(
        rol__in=['admin', 'profesional'],
        servicios_asignados=servicio
    ).distinct()
    
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
    
    # Validación de seguridad: comprobar que el empleado realmente ofrece este servicio
    if not empleado.servicios_asignados.filter(id=servicio.id).exists():
        messages.error(request, f'El profesional {empleado.get_full_name()} no ofrece el servicio "{servicio.nombre_serv}". Por favor, elige otro profesional.')
        return redirect('reserva_paso2', servicio_id=servicio_id)

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
def admin_cambiar_estado(request, pk):
    if not (request.user.is_superuser or request.user.rol in ['admin', 'profesional']):
        messages.error(request, 'No tienes permiso para realizar esta acción.')
        return redirect('reserva_paso1')

    cita = get_object_or_404(Cita, pk=pk)
    
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        
        # Si el estado es "eliminada", ocultamos la cita del dashboard sin borrarla
        if nuevo_estado == 'eliminada':
            cita.oculta_dashboard = True
            cita.save()
            messages.success(request, f'Cita #{cita.id} ocultada del panel rápido (sigue disponible en la gestión de Citas).')
            return redirect(request.META.get('HTTP_REFERER', 'admin_dashboard'))
            
        estados_validos = [opcion[0] for opcion in Cita.ESTADOS_CITA]
        if nuevo_estado in estados_validos:
            cita.estado = nuevo_estado
            cita.save()
            messages.success(request, f'Cita #{cita.id} actualizada a: {cita.get_estado_display()}.')
        else:
            messages.error(request, 'El estado enviado no es válido.')
            
    return redirect(request.META.get('HTTP_REFERER', 'admin_dashboard'))

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

@login_required
def admin_dashboard(request):
    if not (request.user.is_superuser or request.user.rol in ['admin', 'profesional']):
        messages.error(request, 'No tienes permiso para acceder al panel de administración.')
        return redirect('reserva_paso1')

    # 1. Base de la consulta
    citas_qs = (
        Cita.objects
        .filter(oculta_dashboard=False)
        .select_related('cliente', 'empleado')
        .prefetch_related('servicios')
        .order_by('-fecha_hora_cita')
    )

    # 2. Filtro por rol: Si es profesional o admin (pero no superuser), solo ve sus propias citas
    if not request.user.is_superuser and request.user.rol in ['profesional', 'admin']:
        citas_qs = citas_qs.filter(empleado=request.user)
        
        # También filtramos los contadores para que reflejen solo sus citas
        base_count = Cita.objects.filter(oculta_dashboard=False, empleado=request.user)
        total_citas = base_count.count()
        citas_confirmadas = base_count.filter(estado='confirmada').count()
        citas_canceladas = base_count.filter(estado='cancelada').count()
        citas_hoy = base_count.filter(fecha_hora_cita__date=timezone.localdate()).count()
    else:
        # Si es superuser, ve todo el sistema
        total_citas = Cita.objects.filter(oculta_dashboard=False).count()
        citas_confirmadas = Cita.objects.filter(oculta_dashboard=False, estado='confirmada').count()
        citas_canceladas = Cita.objects.filter(oculta_dashboard=False, estado='cancelada').count()
        citas_hoy = Cita.objects.filter(oculta_dashboard=False, fecha_hora_cita__date=timezone.localdate()).count()

    # 3. Datos del gráfico (si es profesional, el gráfico también debería ser solo de sus citas)
    chart_data = obtener_datos_grafico(agrupacion='mes')

    return render(request, 'gestion/dashboard.html', {
        'citas': citas_qs[:10],
        'config': ConfiguracionSistema.objects.first(),
        'total_citas': total_citas,
        'citas_confirmadas': citas_confirmadas,
        'citas_canceladas': citas_canceladas,
        'citas_hoy': citas_hoy,
        'chart_data': chart_data,
    })

# ---------- Citas: listado con filtros ----------
@login_required
def gestion_citas(request):
    if not (request.user.is_superuser or request.user.rol in ['admin', 'profesional']):
        messages.error(request, 'No tienes permiso para acceder a esta sección.')
        return redirect('reserva_paso1')

    qs = (
        Cita.objects
        .select_related('cliente', 'empleado')
        .prefetch_related('servicios')
        .order_by('-fecha_hora_cita')
    )

    # FILTRO CLAVE: Si es profesional, solo ve sus propias citas
    if not request.user.is_superuser and request.user.rol == 'profesional':
        qs = qs.filter(empleado=request.user)

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(cliente__first_name__icontains=q) | Q(cliente__last_name__icontains=q)
            | Q(empleado__first_name__icontains=q) | Q(empleado__last_name__icontains=q)
            | Q(id__icontains=q)
        )

    estado = request.GET.get('estado', '').strip()
    if estado:
        qs = qs.filter(estado=estado)

    page_obj = Paginator(qs, 20).get_page(request.GET.get('page'))

    return render(request, 'gestion/citas.html', {
        'page_obj': page_obj,
        'q': q,
        'estado': estado,
        'estados': Cita.ESTADOS_CITA,
        'config': ConfiguracionSistema.objects.first(),
    })

# ---------- Servicios ----------
@login_required
def gestion_servicios(request):
    if not (request.user.is_superuser or request.user.rol == 'admin'):
        messages.error(request, 'No tienes permiso para acceder a esta sección.')
        return redirect('admin_dashboard')
    servicios = Servicio.objects.all().order_by('nombre_serv')
    return render(request, 'gestion/servicios.html', {
        'servicios': servicios,
        'config': ConfiguracionSistema.objects.first(),
    })

@login_required
def gestion_servicio_form(request, pk=None):
    if not (request.user.is_superuser or request.user.rol in ['admin', 'profesional']):
        messages.error(request, 'No tienes permiso para acceder a esta sección.')
        return redirect('reserva_paso1')

    inst = get_object_or_404(Servicio, pk=pk) if pk else None
    form = ServicioForm(request.POST or None, request.FILES or None, instance=inst)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Servicio guardado correctamente.')
        return redirect('gestion_servicios')
    
    if request.method == 'POST':
        messages.error(request, 'Revisa los datos del formulario.')

    return render(request, 'gestion/servicio_form.html', {
        'form': form, 
        'inst': inst,
        'config': ConfiguracionSistema.objects.first(),
    })

@login_required
def gestion_servicio_eliminar(request, pk):
    if not (request.user.is_superuser or request.user.rol in ['admin', 'profesional']):
        messages.error(request, 'No tienes permiso para acceder a esta sección.')
        return redirect('reserva_paso1')

    servicio = get_object_or_404(Servicio, pk=pk)

    if request.method == 'POST':
        servicio.delete()
        messages.success(request, 'Servicio eliminado.')
        return redirect('gestion_servicios')

    return render(request, 'gestion/confirmar_eliminar.html', {
        'obj': servicio,
        'titulo': f'Eliminar servicio: {servicio.nombre_serv}',
        'cancel_url': 'gestion_servicios',
        'config': ConfiguracionSistema.objects.first(),
    })


# ---------- Profesionales ----------
@login_required
def gestion_profesionales(request):
    if not (request.user.is_superuser or request.user.rol in ['admin', 'profesional']):
        messages.error(request, 'No tienes permiso para acceder a esta sección.')
        return redirect('reserva_paso1')

    profesionales = (
        Usuario.objects
        .filter(rol__in=['profesional', 'admin'])
        .order_by('first_name')
    )
    
    return render(request, 'gestion/profesionales.html', {
        'profesionales': profesionales,
        'config': ConfiguracionSistema.objects.first(),
    })

@login_required
def gestion_profesional_form(request, pk=None):
    if not (request.user.is_superuser or request.user.rol in ['admin', 'profesional']):
        messages.error(request, 'No tienes permiso para acceder a esta sección.')
        return redirect('reserva_paso1')

    inst = get_object_or_404(Usuario, pk=pk) if pk else None
    form = ProfesionalForm(request.POST or None, instance=inst)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profesional guardado correctamente.')
        return redirect('gestion_profesionales')

    if request.method == 'POST':
        messages.error(request, 'Revisa los datos del formulario.')

    return render(request, 'gestion/profesional_form.html', {
        'form': form, 
        'inst': inst,
        'config': ConfiguracionSistema.objects.first(),
    })

# ---------- Disponibilidad ----------
@login_required
def gestion_disponibilidad(request):
    if not (request.user.is_superuser or request.user.rol in ['admin', 'profesional']):
        messages.error(request, 'No tienes permiso para acceder a esta sección.')
        return redirect('reserva_paso1')

    items = (
        Disponibilidad.objects
        .select_related('empleado')
        .order_by('empleado__first_name', 'dia_semana', 'hora_inicio')
    )
    return render(request, 'gestion/disponibilidad.html', {
        'items': items,
        'config': ConfiguracionSistema.objects.first(),
    })

@login_required
def gestion_disponibilidad_form(request, pk=None):
    if not (request.user.is_superuser or request.user.rol in ['admin', 'profesional']):
        messages.error(request, 'No tienes permiso para acceder a esta sección.')
        return redirect('reserva_paso1')

    inst = get_object_or_404(Disponibilidad, pk=pk) if pk else None
    form = DisponibilidadForm(request.POST or None, instance=inst)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Disponibilidad guardada correctamente.')
        return redirect('gestion_disponibilidad')

    if request.method == 'POST':
        messages.error(request, 'Revisa los datos del formulario.')

    return render(request, 'gestion/disponibilidad_form.html', {
        'form': form, 
        'inst': inst,
        'config': ConfiguracionSistema.objects.first(),
    })

@login_required
def gestion_disponibilidad_eliminar(request, pk):
    if not (request.user.is_superuser or request.user.rol in ['admin', 'profesional']):
        messages.error(request, 'No tienes permiso para acceder a esta sección.')
        return redirect('reserva_paso1')

    item = get_object_or_404(Disponibilidad, pk=pk)

    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Disponibilidad eliminada.')
        return redirect('gestion_disponibilidad')

    return render(request, 'gestion/confirmar_eliminar.html', {
        'obj': item,
        'titulo': 'Eliminar disponibilidad',
        'cancel_url': 'gestion_disponibilidad',
        'config': ConfiguracionSistema.objects.first(),
    })


# ---------- Bloqueos ----------
@login_required
def gestion_bloqueos(request):
    if not (request.user.is_superuser or request.user.rol in ['admin', 'profesional']):
        messages.error(request, 'No tienes permiso para acceder a esta sección.')
        return redirect('reserva_paso1')

    items = (
        BloqueoHorario.objects
        .select_related('empleado')
        .order_by('-fecha_inicio')
    )
    return render(request, 'gestion/bloqueos.html', {
        'items': items,
        'config': ConfiguracionSistema.objects.first(),
    })

@login_required
def gestion_bloqueo_form(request, pk=None):
    if not (request.user.is_superuser or request.user.rol in ['admin', 'profesional']):
        messages.error(request, 'No tienes permiso para acceder a esta sección.')
        return redirect('reserva_paso1')

    inst = get_object_or_404(BloqueoHorario, pk=pk) if pk else None
    form = BloqueoForm(request.POST or None, instance=inst)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Bloqueo guardado correctamente.')
        return redirect('gestion_bloqueos')

    if request.method == 'POST':
        messages.error(request, 'Revisa los datos del formulario.')

    return render(request, 'gestion/bloqueo_form.html', {
        'form': form, 
        'inst': inst,
        'config': ConfiguracionSistema.objects.first(),
    })

@login_required
def gestion_bloqueo_eliminar(request, pk):
    if not (request.user.is_superuser or request.user.rol in ['admin', 'profesional']):
        messages.error(request, 'No tienes permiso para acceder a esta sección.')
        return redirect('reserva_paso1')

    item = get_object_or_404(BloqueoHorario, pk=pk)

    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Bloqueo eliminado.')
        return redirect('gestion_bloqueos')

    return render(request, 'gestion/confirmar_eliminar.html', {
        'obj': item,
        'titulo': 'Eliminar bloqueo',
        'cancel_url': 'gestion_bloqueos',
        'config': ConfiguracionSistema.objects.first(),
    })


# ---------- Pagos ----------
@login_required
def gestion_pagos(request):
    if not (request.user.is_superuser or request.user.rol == 'admin'):
        messages.error(request, 'No tienes permiso para acceder a esta sección.')
        return redirect('admin_dashboard')
    qs = Pago.objects.select_related('cita', 'cliente').order_by('-fecha_pago')
    page_obj = Paginator(qs, 30).get_page(request.GET.get('page'))
    total = qs.aggregate(t=Sum('monto'))['t'] or 0
    return render(request, 'gestion/pagos.html', {
        'page_obj': page_obj,
        'total': total,
        'config': ConfiguracionSistema.objects.first(),
    })

# ---------- Configuración ----------
@login_required
def gestion_configuracion(request):
    if not (request.user.is_superuser or request.user.rol == 'admin'):
        messages.error(request, 'No tienes permiso para acceder a esta sección.')
        return redirect('reserva_paso1')

    config = ConfiguracionSistema.objects.first()
    if not config:
        config = ConfiguracionSistema.objects.create()

    form = ConfiguracionForm(request.POST or None, instance=config)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Configuración actualizada.')
        return redirect('gestion_configuracion')

    if request.method == 'POST':
        messages.error(request, 'Revisa los datos del formulario.')

    return render(request, 'gestion/configuracion.html', {'form': form, 'config': config})

def obtener_datos_grafico(fecha_inicio=None, fecha_fin=None, agrupacion='mes'):
    citas = Cita.objects.all()
    
    if fecha_inicio and fecha_fin:
        inicio_dt = datetime.datetime.combine(fecha_inicio, datetime.time.min)
        fin_dt = datetime.datetime.combine(fecha_fin, datetime.time.max)
        
        inicio_dt = timezone.make_aware(inicio_dt, timezone.get_current_timezone())
        fin_dt = timezone.make_aware(fin_dt, timezone.get_current_timezone())
        
        citas = citas.filter(fecha_hora_cita__range=[inicio_dt, fin_dt])

    datos_agrupados = defaultdict(lambda: {'confirmadas': 0, 'canceladas': 0, 'no_asistio': 0})

    for c in citas.values('fecha_hora_cita', 'estado'):
        if not c['fecha_hora_cita']:
            continue
        
        fecha_local = timezone.localtime(c['fecha_hora_cita'])
        
        if agrupacion == 'dia':
            clave = fecha_local.date()
        else:
            clave = fecha_local.date().replace(day=1)
        
        if c['estado'] == 'confirmada':
            datos_agrupados[clave]['confirmadas'] += 1
        elif c['estado'] == 'cancelada':
            datos_agrupados[clave]['canceladas'] += 1
        elif c['estado'] == 'no_asistio':
            datos_agrupados[clave]['no_asistio'] += 1

    claves_ordenadas = sorted(datos_agrupados.keys())

    labels = []
    for k in claves_ordenadas:
        if agrupacion == 'dia':
            labels.append(k.strftime('%d %b').capitalize())
        else:
            labels.append(k.strftime('%b %Y').capitalize())

    return {
        'labels': labels,
        'confirmadas': [datos_agrupados[k]['confirmadas'] for k in claves_ordenadas],
        'canceladas': [datos_agrupados[k]['canceladas'] for k in claves_ordenadas],
        'no_asistio': [datos_agrupados[k]['no_asistio'] for k in claves_ordenadas],
    }

@login_required
def api_datos_grafico(request):
    if not (request.user.is_superuser or request.user.rol in ['admin', 'profesional']):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    periodo = request.GET.get('periodo', 'mes')
    desde_str = request.GET.get('desde')
    hasta_str = request.GET.get('hasta')

    hoy = timezone.localdate()

    if periodo == 'semana':
        fecha_inicio = hoy - datetime.timedelta(days=7)
        fecha_fin = hoy + datetime.timedelta(days=7) # Mostramos la semana pasada y la próxima
        agrupacion = 'dia'
    elif periodo == 'mes':
        # Aquí forzamos a que sea agrupación mensual (Histórico completo)
        fecha_inicio = None
        fecha_fin = None
        agrupacion = 'mes'
    elif periodo == 'rango' and desde_str and hasta_str:
        fecha_inicio = datetime.datetime.strptime(desde_str, '%Y-%m-%d').date()
        fecha_fin = datetime.datetime.strptime(hasta_str, '%Y-%m-%d').date()
        if (fecha_fin - fecha_inicio).days > 60:
            agrupacion = 'mes'
        else:
            agrupacion = 'dia'
    else:
        fecha_inicio = None
        fecha_fin = None
        agrupacion = 'mes'

    data = obtener_datos_grafico(fecha_inicio, fecha_fin, agrupacion)
    return JsonResponse(data)

@login_required
def descargar_reporte_excel(request):
    if not (request.user.is_superuser or request.user.rol in ['admin', 'profesional']):
        return redirect('reserva_paso1')

    periodo = request.GET.get('periodo', 'mes')
    desde_str = request.GET.get('desde')
    hasta_str = request.GET.get('hasta')

    hoy = timezone.localdate()
    citas = Cita.objects.all()

    # Misma lógica que el gráfico
    if periodo == 'semana':
        fecha_inicio = hoy - datetime.timedelta(days=7)
        fecha_fin = hoy + datetime.timedelta(days=7)
        inicio_dt = timezone.make_aware(datetime.datetime.combine(fecha_inicio, datetime.time.min))
        fin_dt = timezone.make_aware(datetime.datetime.combine(fecha_fin, datetime.time.max))
        citas = citas.filter(fecha_hora_cita__range=[inicio_dt, fin_dt])
        
    elif periodo == 'rango' and desde_str and hasta_str:
        fecha_inicio = datetime.datetime.strptime(desde_str, '%Y-%m-%d').date()
        fecha_fin = datetime.datetime.strptime(hasta_str, '%Y-%m-%d').date()
        inicio_dt = timezone.make_aware(datetime.datetime.combine(fecha_inicio, datetime.time.min))
        fin_dt = timezone.make_aware(datetime.datetime.combine(fecha_fin, datetime.time.max))
        citas = citas.filter(fecha_hora_cita__range=[inicio_dt, fin_dt])

    citas = citas.select_related('cliente', 'empleado').order_by('-fecha_hora_cita')

    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte de Citas"

    headers = ['ID', 'Cliente', 'Profesional', 'Fecha y Hora', 'Estado', 'Monto Abono']
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="D98F96", end_color="D98F96", fill_type="solid")
        cell.alignment = Alignment(horizontal="center")

    for c in citas:
        ws.append([
            c.id,
            c.cliente.get_full_name() or c.cliente.username,
            c.empleado.get_full_name() or c.empleado.username,
            timezone.localtime(c.fecha_hora_cita).strftime('%d/%m/%Y %H:%M'),
            c.get_estado_display(),
            float(c.monto_abono)
        ])

    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        ws.column_dimensions[column].width = adjusted_width

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="reporte_citas.xlsx"'
    wb.save(response)
    return response

# --------------------------------------------------
# VISTA PARA DESCARGAR PDF
# --------------------------------------------------
@login_required
def descargar_reporte_pdf(request):
    if not (request.user.is_superuser or request.user.rol in ['admin', 'profesional']):
        return redirect('reserva_paso1')

    periodo = request.GET.get('periodo', 'mes')
    desde_str = request.GET.get('desde')
    hasta_str = request.GET.get('hasta')

    hoy = timezone.localdate()
    citas = Cita.objects.all()

    # Misma lógica que el gráfico
    if periodo == 'semana':
        fecha_inicio = hoy - datetime.timedelta(days=7)
        fecha_fin = hoy + datetime.timedelta(days=7)
        inicio_dt = timezone.make_aware(datetime.datetime.combine(fecha_inicio, datetime.time.min))
        fin_dt = timezone.make_aware(datetime.datetime.combine(fecha_fin, datetime.time.max))
        citas = citas.filter(fecha_hora_cita__range=[inicio_dt, fin_dt])
        
    elif periodo == 'rango' and desde_str and hasta_str:
        fecha_inicio = datetime.datetime.strptime(desde_str, '%Y-%m-%d').date()
        fecha_fin = datetime.datetime.strptime(hasta_str, '%Y-%m-%d').date()
        inicio_dt = timezone.make_aware(datetime.datetime.combine(fecha_inicio, datetime.time.min))
        fin_dt = timezone.make_aware(datetime.datetime.combine(fecha_fin, datetime.time.max))
        citas = citas.filter(fecha_hora_cita__range=[inicio_dt, fin_dt])

    citas = citas.select_related('cliente', 'empleado').order_by('-fecha_hora_cita')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_citas.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    titulo = Paragraph("Reporte de Citas - RG Beauty Spa", styles['Title'])
    elements.append(titulo)
    elements.append(Paragraph(f"Generado el: {timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    elements.append(Paragraph("<br/><br/>", styles['Normal']))

    data = [['ID', 'Cliente', 'Profesional', 'Fecha/Hora', 'Estado', 'Abono']]
    for c in citas:
        data.append([
            str(c.id),
            c.cliente.get_full_name() or c.cliente.username,
            c.empleado.get_full_name() or c.empleado.username,
            timezone.localtime(c.fecha_hora_cita).strftime('%d/%m/%Y %H:%M'),
            c.get_estado_display(),
            f"${c.monto_abono:,.0f}"
        ])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#D98F96")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#FFF4F4")),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#EBE7E8")),
    ]))

    elements.append(table)
    doc.build(elements)
    return response