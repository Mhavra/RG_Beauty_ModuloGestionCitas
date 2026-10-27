from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone

# Create your models here.
class Rol(models.Model):
    nombre_rol = models.CharField(max_length=14)

class Perfil(models.Model):
    nombre = models.CharField(max_length=100)
    correo = models.EmailField()
    telefono = models.IntegerField(max_length=11)
    rol = models.ForeignKey(
        Rol,
        on_delete=models.CASCADE,
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    def __str__(self):
        return self.nombre

class Servicio(models.Model):
    nombre_servicio = models.CharField(max_length=100)
    precio = models.IntegerField()
    empleado_asignado = models.ForeignKey(
        Perfil,
        on_delete=models.CASCADE,
        related_name='servicio'
    )
    def __str__(self):
        return self.nombre_servicio

class Cita(models.Model):
    fecha_cita = models.DateField

    pass

class Venta(models.Model):
    cliente = models.ForeignKey(
        Perfil,
        on_delete=models.RESTRICT,
        related_name= 'ventas'
    )
    pass

class Disponibilidad(models.Model):
    DIAS_SEMANA = (
        ('luneas', 'Lunes'),
        ('martes', 'Martes',),
        ('miercoles', 'Miercoles'),
        ('jueves', 'Jueves'),
        ('viernes', 'Viernes'),
        ('sabado', 'Sabado'),
        ('domingo', 'Domingo'),
    )

    empleado = models.ForeignKey (
        Usuario,
        on_delete=models.CASCADE,
        related_name='disponibilidades',
        limit_choices_to={'rol__in': ['profesional', 'admin']},
        verbose_name="Profesional"
    )
    dia_semana = models.CharField(max_length=10, choices=DIAS_SEMANA, verbose_name="Día de la Semana")
    hora_inicio = models.TimeField(verbose_name="Hora Inicio")
    hora_fin = models.TimeField(verbose_name="Hora Fin")

    class Meta:
        verbose_name = "Disponibilidad Horaria"
        verbose_name_plural = "Disponibilidad Horarias"
        unique_together = ('empleado', 'dia_semana', 'hora_inicio')

    def clean(self):
        if self.hora_inicio and self.hora_fin and self.hora_inicio >= self.hora_fin:
            raise ValidationError("La hora de inicio debe ser anterior a la hora de término")
        
    def __str__(self):
        return f"Bloqueo {self.empleado.get_full_name()}: {self.fecha_inicio.strftime('%d/%m/%Y %H:%M')} al {self.fecha_fin.strftime('%d/%m/%Y %H:%M')}"
    pass

class BloqueoHorario(models.Model):
    pass

class Configuracion_Sistema(models.Model):
    pass

class Pago(models.Model): 
    pass