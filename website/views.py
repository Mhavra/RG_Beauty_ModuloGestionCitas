from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages


# Create your views here.
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
from .forms import RegistroClienteForm, LoginForm, FiltroReporteForm



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

 
def reserva_paso1_servicios(request): 
    servicios = Servicio.objects.all() 
    return render(request, 'reserva_paso1_servicios.html', {'servicios': servicios}) 

 
def reserva_paso2_fecha(request, servicio_id): 
    servicio = get_object_or_404(Servicio, pk=servicio_id) 
    profesionales = Usuario.objects.filter(rol__in=['admin', 'profesional']) 
    return render(request, 'reserva_paso2_fecha.html', {'servicio': servicio, 'profesionales': profesionales})


def reserva_paso3_horarios(request, servicio_id, empleado_id): 
    servicio = get_object_or_404(Servicio, pk=servicio_id) 
    empleado = get_object_or_404(Usuario, pk=empleado_id) 
    fecha_str = request.GET.get('fecha', datetime.date.today().strftime('%Y-%m-%d')) 
    horarios_libres = ['09:00', '11:00', '15:00', '17:00'] 
    return render(request, 'reserva_paso3_horarios.html', {'servicio': servicio, 'empleado': empleado, 'fecha': fecha_str, 'horarios': horarios_libres}) 

 
@login_required 
def reserva_paso4_resumen(request): 
    servicio_id = request.POST.get('servicio_id') 
    empleado_id = request.POST.get('empleado_id') 
    fecha_hora_str = request.POST.get('fecha_hora') 
     
    servicio = get_object_or_404(Servicio, pk=servicio_id) 
    empleado = get_object_or_404(Usuario, pk=empleado_id) 
     
    config = ConfiguracionSistema.objects.first() 
    porcentaje = config.porcentaje_abono if config else 50.00 
     
    monto_total = servicio.precio_serv 
    if config and config.permite_monto_fijo: 
        monto_abono = config.monto_fijo_abono 
    else: 
        monto_abono = (monto_total * (porcentaje / 100)) 
         
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
        monto_abono = request.POST.get('monto_abono') 
        metodo_pago = request.POST.get('metodo_pago', 'webpay') 
         
        fecha_hora = datetime.datetime.strptime(fecha_hora_str, '%Y-%m-%d %H:%M') 
         
        try: 
            with transaction.atomic(): 
                cita_existente = Cita.objects.select_for_update().filter( 
                    empleado_id=empleado_id, fecha_hora_cita=fecha_hora, estado__in=['confirmada', 'pendiente'] 
                ).exists() 
                 
                if cita_existente: 
                    return JsonResponse({'status': 'error', 'message': 'El horario seleccionado acaba de ser reservado.'}, status=409) 
                 
                nueva_cita = Cita.objects.create( 
                    cliente=request.user, empleado_id=empleado_id, fecha_hora_cita=fecha_hora, 
                    estado='confirmada', monto_abono=monto_abono, estado_abono='pagado' 
                ) 
                servicio = Servicio.objects.get(pk=servicio_id) 
                CitaServicio.objects.create(cita=nueva_cita, servicio=servicio) 
                 
                Pago.objects.create( 
                    cita=nueva_cita, cliente=request.user, monto=monto_abono, 
                    metodo_pago=metodo_pago, tipo_pago='abono', estado='completado', 
                    transaccion_id=f"PAY-{nueva_cita.id}-{int(datetime.datetime.now().timestamp())}" 
                ) 
                 
                despachar_notificacion_cita(nueva_cita) 
                return redirect('reserva_paso6_exito', cita_id=nueva_cita.id) 
                 
        except Exception as e: 
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)



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
    if request.user.rol not in ['admin', 'profesional']: 
        return redirect('reserva_paso1') 
    citas = Cita.objects.all().order_by('-fecha_hora_cita') 
    form_reporte = FiltroReporteForm() 
    config = ConfiguracionSistema.objects.first() 
    return render(request, 'admin_dashboard.html', {'citas': citas, 'form_reporte': form_reporte, 'config': config})

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