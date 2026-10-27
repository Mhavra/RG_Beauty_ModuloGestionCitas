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
            return f"{self.nombre_serv}
            ({self.duracion_minutos}min) - $
            {self.precio_serv:,.0f}"