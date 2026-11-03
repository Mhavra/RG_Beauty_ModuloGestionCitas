from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone


# Create your models here.

#validador de numero de telefono chileno
telefono_validator = RegexValidator(
    regex=r'^\+569\d{8}$',
    message= 'EL numero de telefono debe tener el formato chileno, prefijo +569 y 8 digitos, ejemplo: +56912345678'
)

#usuario personalizado
class Usuario(AbstractUser):
    ROLES = (
        ('cliente', 'Cliente'),
        ('profesional', 'Profesional', 'Estilista'),
        ('admin', 'Administradora'),
    ),
    #email personalizado para que tengan uno unico para iniciar sesion como otra opcion
    email =models.EmailField(
        unique=True,
        verbose_name='Correo Electronico',
        error_messages={
                        'unique': 'Ya existe un usuario con este correo electronico'
                        }
        )
    rol = models.CharField(
        max_length= 20, 
        choices= ROLES,
        default= 'cliente',
        verbose_name='Rol de usuario'
        )
    telefono = models.CharField(
        max_length=12,
        validators=[telefono_validator],
        verbose_name='Numero de telefono (+569)',
        help_text='Formato: +56912345678'
        )

    #campo json nativo para preferencias esteticas e historial estetico

    #username field para que se pueda iniciar sesion con el correo electronico
    USERNAME_FIELD = 'email'
    #required fields para que se pueda crear un usuario con el correo electronico y el username
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        #esto es para que se vea en el admin de django con el nombre de usuario y no como user
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_rol_display()})"
        #get_full_name() es para que se vea el nombre completo del usuario y no el username
        #get_rol_display() es para que se vea el nombre del rol y no el valor 

    #config del sistema
class ConfiguracionSistema(models.Model):
    #este es un modelo para guardar la configuracion del sistema, como el porcentaje de abono requerido y si se permite monto fijo
    porcentaje_abono = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=50.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Porcentaje de abono requerido (%)',
        help_text= 'Porcentaje cobrado al confirmar reserva, ej: 50.00 para 50%'
        )
    permite_monto_fijo = models.BooleanField(
        default=False,
        verbose_name='¿Usar monto fijo en vez de porcentaje?',
        )
    monto_fijo_abono = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        verbose_name='Monto Fijo de Abono (CLP)'
        )
    ultima_modificacion = models.DateTimeField(
        auto_now=True,
        verbose_name='Ultima Modificacion'
        )

    class Meta:
        #esto son para que se vea en el admin de django con el nombre de configuracion del sistema y no como configuracionsistema
        verbose_name = 'Configuracion del Sistema'
        verbose_name_plural = 'Configuraciones del Sistema'

    def __str__(self):
        if self.permite_monto_fijo:
            return f'COnfiguración activa: Abono Fijo de ${self.monto_fijo_abono:,.0f} CLP'
        else:
            return f'Configuración activa: Abono del {self.porcentaje_abono:.2f}%'


class Servicio(models.Model):
    nombre_serv = models.CharField(max_length=100, verbose_name="Nombre del servicio")
    duracion_minutos = models.PositiveIntegerField(validators=[MinValueValidator(15)], 
    verbose_name="Duracion(minutos)", help_text="Duracion real en minutos (ej:90 oara corte, 300 para mechas).")
    precio_serv = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)],
    verbose_name="Precio total (CLP)")

    class Meta:
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"

        def __str__(self):
            return f"{self.nombre_serv}({self.duracion_minutos}min) - ${self.precio_serv:,.0f}"

#disponibilidad horaria semanal
class Disponibilidad(models.Model):
    DIAS_SEMANA= (
            ('Lunes', 'Lunes'),
            ('Martes', 'Martes'),
            ('Miercoles', 'Miercoles'),
            ('Jueves', 'Jueves'),
            ('Viernes', 'Viernes'),
            ('Sabado', 'Sabado'),
            ('Domingo', 'Domingo'),
    )
    empleado = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='disponibilidades',
        limit_choices_to={'rol__in':
                          ['profesional', 'admin']},
                          verbose_name= "PRofesional"
    )
    dia_semana= models.CharField(
        max_length=10,
        choices= DIAS_SEMANA,
        verbose_name= "Dia de la semana"
        )
    hora_inicio= models.TimeField(
        verbose_name= "Hora de inicio"
        )
    hora_fin= models.TimeField(
        verbose_name= "Hora de fin"
        )
    
    class Meta: 
        verbose_name= "Disponibilidad horaria"
        verbose_name_plural= "Disponibilidades horarias"
        unique_together=(
            #este se usa para que no se repita la disponibilidad de un mismo empleado en el mismo dia y hora
            'empleado',
            'dia_semana',
            'hora_inicio'
        )
    
    def clean(self):
        if self.hora_inicio and self.hora_fin and self.hora_inicio >= self.hora_fin:
            raise ValidationError({'hora_inicio': 'La hora de inicio debe ser menor que la hora de fin.'})
        
    def __str__(self):
        return f"{self.empleado.get_full_name()} - {self.get_dia_semana_display()}: {self.hora_inicio.strftime('%H:%M')} - {self.hora_fin.strftime('%H:%M')}"
    
#bloqueo de horarios (vacaciones, feriados, colacion, descansos)
class BLoqueoHorario(models.Model):
    empleado = models.ForeignKey(
        Usuario,
        on_delete= models.CASCADE,
        related_name='bloqueos',
        limit_choices_to={'rol__in': ['profesional', 'admin']},
        verbose_name= "Profesional"
    )
    fecha_inicio =  models.DateField(verbose_name="Fecha/Hora inicio de bloqueo")
    fecha_fin= models.DateField(verbose_name="Fecha/Hora fin de bloqueo")
    motivo= models.CharField(
        max_length=250,
        default="Descanso / No disponible",
        verbose_name= "Motivo del bloqueo"
    )

    class Meta:
        verbose_name= "Bloqueo de horario"
        verbose_name_plural= "Bloqueos de horarios"

    def clean(self):
        if self.fecha_inicio and self.fecha_fin and self.fecha_inicio >= self.fecha_fin:
            raise ValidationError({'fecha_inicio': 'La fecha de inicio debe ser menor o igual a la fecha de fin.'})
        
    def __str__(self):
        return f"Bloqueo {self.empleado.get_full_name()}: {self.fecha_inicio.strftime('%d/%m/%Y %H:%M')} al {self.fecha_fin.strftime('%d/%%m/%Y %H:%M')} - Motivo: {self.motivo}"
    
#Cita /Reserva
class Cita(models.Model):
    ESTADOS_CITA = (
        ('pendiente', 'Pendiente de abono'),
        ('confirmada', 'Confirmada con abono'),
        ('completada', 'Atencion completada'),
        ('cancelada', 'Cancelada'),
        ('no_asistio', 'No asistio'),
    )
    ESTADOS_ABONO = (
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
        ('reembolsado', 'Reembolsado'),
    )
    cliente = models.ForeignKey(
        Usuario,
        on_delete=models.RESTRICT,
        related_name='citas_cliente',
        limit_choices_to={'rol': 'cliente'},
        verbose_name="Cliente"
    )
    empleado = models.ForeignKey(
        Usuario,
        on_delete=models.RESTRICT,
        related_name='citas_atendidas',
        limit_choices_to={'rol__in': ['profesional', 'admin']},
        verbose_name="Profesional Atendente"
    )
    servicios = models.ManyToManyField(Servicio, through='CitaServicio', verbose_name="Servicios Reservados")

    fecha_hora_cita = models.DateTimeField(verbose_name="Fecha y Hora de Cita")
    estado = models.CharField(max_length=20, choices=ESTADOS_CITA, default='pendiente', verbose_name="Estado de Cita")

    monto_abono = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        verbose_name="Monto de Abono (CLP)"
    )
    estado_abono = models.CharField(max_length=20, choices=ESTADOS_ABONO, default='pendiente', verbose_name="Estado del Abono")

    historial_notificaciones = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Historial de Notificaciones",
        help_text="Registro de envíos por WhatsApp API y conmutación a correo de respaldo (SMTP)."
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")

    class Meta:
        verbose_name = "Cita"
        verbose_name_plural = "Citas"
        ordering = ['-fecha_hora_cita']

    def __str__(self):
        return f"Cita #{self.id} - {self.cliente.get_full_name()} con {self.empleado.get_full_name()} ({self.fecha_hora_cita.strftime('%d/%m/%Y %H:%M')})"

#Citas-servicios intermedia
class CitaServicio(models.Model):
    cita = models.ForeignKey(Cita, on_delete=models.CASCADE)
    servicio = models.ForeignKey(Servicio, on_delete=models.RESTRICT)

    class Meta:
        verbose_name = "Servicio de Cita"
        verbose_name_plural = "Servicios de Citas"
        unique_together = ('cita', 'servicio')

    def __str__(self):
        return f"Cita #{self.cita.id} - Servicio: {self.servicio.nombre_serv}"

#REgistro de pagos y abonos de este modulo
class Pago(models.Model):
    METODOS_PAGO = (
        ('efectivo', 'Efectivo en Salón'),
        ('debito', 'Débito en Salón'),
        ('credito', 'Crédito en Salón'),
        ('mercadopago', 'Mercado Pago'),
        ('webpay', 'Webpay Plus'),
    )
    TIPOS_PAGO = (
        ('abono', 'Abono'),
        ('saldo', 'Saldo Restante en Salón'),
        ('total', 'Pago Total'),
        ('reembolso', 'Reembolso'),
    )
    ESTADOS_PAGO = (
        ('pendiente', 'Pendiente'),
        ('completado', 'Completado'),
        ('rechazado', 'Rechazado'),
        ('reembolsado', 'Reembolsado'),
    )

    cita = models.ForeignKey(
        Cita,
        on_delete=models.CASCADE,
        related_name='pagos',
        verbose_name="Cita Asociada"
    )
    cliente = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='pagos', verbose_name="Usuario que Paga")
    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Monto Pagado (CLP)"
    )
    metodo_pago = models.CharField(max_length=30, choices=METODOS_PAGO, verbose_name="Método de Pago")
    tipo_pago = models.CharField(max_length=30, choices=TIPOS_PAGO, verbose_name="Tipo de Pago")
    estado = models.CharField(max_length=30, choices=ESTADOS_PAGO, default='completado', verbose_name="Estado del Pago")
    fecha_pago = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Pago")
    transaccion_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="ID Transacción Pasarela",
        help_text="Identificador único devuelto por Mercado Pago / WebPay"
    )

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"

    def __str__(self):
        return f"Pago ${self.monto:,.0f} ({self.get_tipo_pago_display()}) - Cita #{self.cita.id}"