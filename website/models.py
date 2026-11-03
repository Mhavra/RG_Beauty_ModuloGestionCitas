from django.db import models
from django.contrib.auth.models import AbstractUser
#from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
#from django.core.exceptions import ValidationError
#from django.utils import timezone
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