from django.db import models
from django.contrib.auth.models import User

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
    
    pass

class BloqueoHorario(models.Model):
    pass

class Configuracion_Sistema(models.Model):
    pass

class Pago(models.Model):
    metodos_pago = (
        ('efectivo', 'Efectivo en Salon'), ('debito', 'Débito en Salon'), ('credito', 'Crédito en Salon'), ('mercadopago', 'Mercado Pago'), ('webpay', 'Webpay Plus'),
        )
    tipos_pago = (
        ('abono', 'Abono'), ('saldo', 'Saldo Restante en Salon'), ('total', 'Pago Total'), ('reembolso', 'Reembolso'),
        )
    estados_pago = (('pendiente', 'Pendiente'), ('completado', 'Completado'), ('rechazado', 'Rechazado'), ('reembolsado', 'Reembolsado'),
        )
    cita = models.ForeignKey(
        Cita,
        on_delete=models.CASCADE,
    )
    venta =   
    pass