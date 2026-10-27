from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

#validador de numero de telefono

#usuario personalizado
class Usuario(AbstractUser):
    ROLES = (
        ('cliente', 'Cliente'),
        ('profesional', 'Profesional', 'Estilista'),
        ('admin', 'Administradora'),
    ),
    #email personalizado para que tengan uno unico para iniciar sesion como otra opcion
    email =models.EmailField(unique=True,
                             
                             )

    rol = models.CharField(max_length= 20, choices= ROLES,)