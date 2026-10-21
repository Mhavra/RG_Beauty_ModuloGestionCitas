from django.db import models

# Create your models here.

class Usuario(models.Model):
    
    rol = models.ForeignKey(
        Roles,
        on_delete=models.CASCADE,
        related_name='usuarios'
    )

    def __str__(self):
        return self.nombre_us
    
class Disponibilidad(models.Model):
    pass


class Venta(models.Model):
    pass



class Cita(models.Model):
    pass


class Producto(models.Model):
    pass


class Detalle_venta(models.Model):
    pass

class Pago(models.Model):
    pass