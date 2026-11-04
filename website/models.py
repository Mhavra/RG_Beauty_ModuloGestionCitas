from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone


telefono_validator = RegexValidator(
    regex=r'^\+569\d{8}$',
    message='El número de teléfono debe tener el formato chileno: +569XXXXXXXX'
)


class Usuario(AbstractUser):
    ROLES = (
        ('cliente', 'Cliente'),
        ('profesional', 'Profesional'),
        ('admin', 'Administradora'),
        ('estilista', 'Estilista'),
    )
    email = models.EmailField(
        unique=True,
        verbose_name='Correo Electrónico',
        error_messages={'unique': 'Ya existe un usuario con este correo electrónico'}
    )
    rol = models.CharField(max_length=20, choices=ROLES, default='cliente', verbose_name='Rol de usuario')
    telefono = models.CharField(
        max_length=12,
        validators=[telefono_validator],
        verbose_name='Número de teléfono (+569)',
        help_text='Formato: +56912345678'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_rol_display()})"


class ConfiguracionSistema(models.Model):
    porcentaje_abono = models.DecimalField(
        max_digits=5, decimal_places=2, default=50.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Porcentaje de abono requerido (%)',
        help_text='Porcentaje cobrado al confirmar reserva, ej: 50.00'
    )
    permite_monto_fijo = models.BooleanField(default=False, verbose_name='¿Usar monto fijo?')
    monto_fijo_abono = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        validators=[MinValueValidator(0)],
        verbose_name='Monto Fijo de Abono (CLP)'
    )
    ultima_modificacion = models.DateTimeField(auto_now=True, verbose_name='Última Modificación')

    class Meta:
        verbose_name = 'Configuración del Sistema'
        verbose_name_plural = 'Configuraciones del Sistema'

    def __str__(self):
        if self.permite_monto_fijo:
            return f'Abono Fijo de ${self.monto_fijo_abono:,.0f} CLP'
        return f'Abono del {self.porcentaje_abono:.2f}%'


# NUEVO: catálogo de Servicios (uno a muchos)
class Categoria(models.Model):
    nombre = models.CharField(max_length=50, unique=True, verbose_name='Nombre de la categoría')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


# NUEVO: etiquetas reutilizables para Servicios (muchos a muchos)
class Etiqueta(models.Model):
    nombre = models.CharField(max_length=30, unique=True, verbose_name='Etiqueta')
    color = models.CharField(max_length=7, default='#f4c2c2', verbose_name='Color HEX')

    class Meta:
        verbose_name = 'Etiqueta'
        verbose_name_plural = 'Etiquetas'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Servicio(models.Model):
    imagen = models.ImageField(upload_to='servicios/', blank=True, null=True)
    nombre_serv = models.CharField(max_length=100, verbose_name='Nombre del servicio')
    duracion_minutos = models.PositiveIntegerField(
        validators=[MinValueValidator(15)],
        verbose_name='Duración (minutos)',
        help_text='Duración real en minutos (ej: 90 para corte, 300 para mechas)'
    )
    precio_serv = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Precio total (CLP)'
    )
    # NUEVO: catálogo y etiquetas
    categoria = models.ForeignKey(
        Categoria, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='servicios', verbose_name='Categoría'
    )
    etiquetas = models.ManyToManyField(
        Etiqueta, related_name='servicios', blank=True, verbose_name='Etiquetas'
    )

    class Meta:
        verbose_name = 'Servicio'
        verbose_name_plural = 'Servicios'
        ordering = ['nombre_serv']

    def __str__(self):
        return f"{self.nombre_serv} ({self.duracion_minutos}min) - ${self.precio_serv:,.0f}"


class Disponibilidad(models.Model):
    DIAS_SEMANA = (
        ('Lunes', 'Lunes'), ('Martes', 'Martes'), ('Miercoles', 'Miércoles'),
        ('Jueves', 'Jueves'), ('Viernes', 'Viernes'), ('Sabado', 'Sábado'),
        ('Domingo', 'Domingo'),
    )
    empleado = models.ForeignKey(
        Usuario, on_delete=models.CASCADE,
        related_name='disponibilidades',
        limit_choices_to={'rol__in': ['profesional', 'admin', 'estilista']},
        verbose_name='Profesional'
    )
    dia_semana = models.CharField(max_length=10, choices=DIAS_SEMANA, verbose_name='Día de la semana')
    hora_inicio = models.TimeField(verbose_name='Hora de inicio')
    hora_fin = models.TimeField(verbose_name='Hora de fin')

    class Meta:
        verbose_name = 'Disponibilidad horaria'
        verbose_name_plural = 'Disponibilidades horarias'
        unique_together = ('empleado', 'dia_semana', 'hora_inicio')

    def clean(self):
        if self.hora_inicio and self.hora_fin and self.hora_inicio >= self.hora_fin:
            raise ValidationError({'hora_inicio': 'La hora de inicio debe ser menor que la hora de fin.'})

    def __str__(self):
        return f"{self.empleado.get_full_name()} - {self.get_dia_semana_display()}: {self.hora_inicio:%H:%M} - {self.hora_fin:%H:%M}"


class BloqueoHorario(models.Model):
    empleado = models.ForeignKey(
        Usuario, on_delete=models.CASCADE,
        related_name='bloqueos',
        limit_choices_to={'rol__in': ['profesional', 'admin', 'estilista']},
        verbose_name='Profesional'
    )
    fecha_inicio = models.DateField(verbose_name='Fecha inicio de bloqueo')
    fecha_fin = models.DateField(verbose_name='Fecha fin de bloqueo')
    motivo = models.CharField(max_length=250, default='Descanso / No disponible', verbose_name='Motivo del bloqueo')

    class Meta:
        verbose_name = 'Bloqueo de horario'
        verbose_name_plural = 'Bloqueos de horarios'

    def clean(self):
        if self.fecha_inicio and self.fecha_fin and self.fecha_inicio >= self.fecha_fin:
            raise ValidationError({'fecha_inicio': 'La fecha de inicio debe ser menor o igual a la fecha de fin.'})

    def __str__(self):
        return f"Bloqueo {self.empleado.get_full_name()}: {self.fecha_inicio:%d/%m/%Y} al {self.fecha_fin:%d/%m/%Y} - {self.motivo}"


class Cita(models.Model):
    ESTADOS_CITA = (
        ('pendiente', 'Pendiente de abono'),
        ('confirmada', 'Confirmada con abono'),
        ('completada', 'Atención completada'),
        ('cancelada', 'Cancelada'),
        ('no_asistio', 'No asistió'),
    )
    ESTADOS_ABONO = (
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
        ('reembolsado', 'Reembolsado'),
    )
    cliente = models.ForeignKey(
        Usuario, on_delete=models.RESTRICT,
        related_name='citas_cliente',
        limit_choices_to={'rol': 'cliente'},
        verbose_name='Cliente'
    )
    empleado = models.ForeignKey(
        Usuario, on_delete=models.RESTRICT,
        related_name='citas_atendidas',
        limit_choices_to={'rol__in': ['profesional', 'admin', 'estilista']},
        verbose_name='Profesional Atendente'
    )
    servicios = models.ManyToManyField(Servicio, through='CitaServicio', verbose_name='Servicios Reservados')
    fecha_hora_cita = models.DateTimeField(verbose_name='Fecha y Hora de Cita')
    estado = models.CharField(max_length=20, choices=ESTADOS_CITA, default='pendiente', verbose_name='Estado de Cita')
    monto_abono = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        validators=[MinValueValidator(0)],
        verbose_name='Monto de Abono (CLP)'
    )
    estado_abono = models.CharField(
        max_length=20, choices=ESTADOS_ABONO,
        default='pendiente', verbose_name='Estado del Abono'
    )
    historial_notificaciones = models.JSONField(
        default=list, blank=True,
        verbose_name='Historial de Notificaciones',
        help_text='Registro de envíos por WhatsApp API y correo de respaldo.'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')

    class Meta:
        verbose_name = 'Cita'
        verbose_name_plural = 'Citas'
        ordering = ['-fecha_hora_cita']

    def __str__(self):
        return f"Cita #{self.id} - {self.cliente.get_full_name()} con {self.empleado.get_full_name()} ({self.fecha_hora_cita:%d/%m/%Y %H:%M})"

    @property
    def monto_total_servicios(self):
        return sum(s.precio_serv for s in self.servicios.all())


class CitaServicio(models.Model):
    cita = models.ForeignKey(Cita, on_delete=models.CASCADE)
    servicio = models.ForeignKey(Servicio, on_delete=models.RESTRICT)

    class Meta:
        verbose_name = 'Servicio de Cita'
        verbose_name_plural = 'Servicios de Citas'
        unique_together = ('cita', 'servicio')

    def __str__(self):
        return f"Cita #{self.cita.id} - {self.servicio.nombre_serv}"


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
    cita = models.ForeignKey(Cita, on_delete=models.CASCADE, related_name='pagos', verbose_name='Cita Asociada')
    cliente = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='pagos', verbose_name='Usuario que Paga')
    monto = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='Monto Pagado (CLP)')
    metodo_pago = models.CharField(max_length=30, choices=METODOS_PAGO, verbose_name='Método de Pago')
    tipo_pago = models.CharField(max_length=30, choices=TIPOS_PAGO, verbose_name='Tipo de Pago')
    estado = models.CharField(max_length=30, choices=ESTADOS_PAGO, default='completado', verbose_name='Estado del Pago')
    fecha_pago = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Pago')
    transaccion_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='ID Transacción')

    class Meta:
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'

    def __str__(self):
        return f"Pago ${self.monto:,.0f} ({self.get_tipo_pago_display()}) - Cita #{self.cita.id}"