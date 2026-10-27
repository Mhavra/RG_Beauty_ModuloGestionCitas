from django.db import models
from django.contrib.auth.models import AbstractUser

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

    #campo