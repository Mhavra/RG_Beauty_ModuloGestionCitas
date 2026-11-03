from django.db import models
from django.core.validators import MinValueValidator
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
        related_name='ventas',
        verbose_name="Cliente"
    )
    
    fecha_hora = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora")
    total = models.DecimalField(
        max_digits=10, 
        decimal_places=0,
        default=0, 
        validators=[MinValueValidator(0)],
        verbose_name="Total Venta"
    )

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ['-fecha_hora']

    def __str__(self):
        return f"Venta #{self.id} - {self.cliente.nombre} - ${self.total}"

    def calcular_total(self):
        # Método para recalcular el total basado en los detalles
        self.total = sum(detalle.subtotal for detalle in self.detalles.all())
        self.save()

class DetalleVenta(models.Model):
    # Clase necesaria para la relación 1 a N con Venta (según Diagrama de Clases)
    venta = models.ForeignKey(
        Venta, 
        on_delete=models.CASCADE, 
        related_name='detalles'
    )
    producto = models.ForeignKey(
        'Producto', # Asegúrate de que este sea el nombre de tu modelo de productos
        on_delete=models.RESTRICT
    )
    cantidad = models.PositiveIntegerField(default=1)
    subtotal = models.DecimalField(max_digits=10, decimal_places=0)

    def save(self, *args, **kwargs):
        # Calcula el subtotal automáticamente antes de guardar
        if self.producto:
            self.subtotal = self.producto.precio * self.cantidad
        super().save(*args, **kwargs)

class Disponibilidad(models.Model):
    
    pass

class BloqueoHorario(models.Model):
    pass

class Configuracion_Sistema(models.Model):
    pass

class Pago(models.Model):
    metodos_pago = (
        ('efectivo', 'Efectivo en Salon'), 
        ('debito', 'Débito en Salon'), 
        ('credito', 'Crédito en Salon'), 
        ('mercadopago', 'Mercado Pago'), 
        ('webpay', 'Webpay Plus'),
    )
    tipos_pago = (
        ('abono', 'Abono'), 
        ('saldo', 'Saldo Restante en Salon'), 
        ('total', 'Pago Total'), 
        ('reembolso', 'Reembolso'),
    )
    estados_pago = (
        ('pendiente', 'Pendiente'), 
        ('completado', 'Completado'), 
        ('rechazado', 'Rechazado'), 
        ('reembolsado', 'Reembolsado'),
    )
    
    # --- Relaciones ---
    cita = models.ForeignKey(
        Cita,
        on_delete=models.SET_NULL, # Si se borra la cita, el pago queda como registro histórico
        null=True,
        blank=True,
        related_name='pagos',
        verbose_name="Cita Asociada"
    )
    venta = models.ForeignKey(
        Venta,
        on_delete=models.SET_NULL, # Un pago puede estar asociado a una venta de productos
        null=True,
        blank=True,
        related_name='pagos',
        verbose_name="Venta Asociada"
    )
    
    # --- Campos del Pago ---
    monto = models.DecimalField(
        max_digits=10, 
        decimal_places=0,
        validators=[MinValueValidator(0)],
        verbose_name="Monto del Pago"
    )
    metodo = models.CharField(
        max_length=20, 
        choices=metodos_pago, 
        default='mercadopago',
        verbose_name="Método de Pago"
    )
    tipo = models.CharField(
        max_length=20, 
        choices=tipos_pago, 
        default='abono',
        verbose_name="Tipo de Pago"
    )
    estado = models.CharField(
        max_length=20, 
        choices=estados_pago, 
        default='pendiente',
        verbose_name="Estado del Pago"
    )
    
    # --- Datos de Transacción (Pasarela) ---
    # El CU-05 menciona el webhook asíncrono de la pasarela
    referencia_externa = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        help_text="ID de transacción de Mercado Pago o Webpay"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_pago = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Pago {self.id} - {self.get_tipo_display()} - ${self.monto} ({self.get_estado_display()})"

    def clean(self):
        from django.core.exceptions import ValidationError
        # Validación de negocio: Un pago debe estar asociado a una Cita o a una Venta, pero no a ambas a la vez.
        if self.cita and self.venta:
            raise ValidationError("Un pago no puede estar asociado simultáneamente a una cita y a una venta.")
        if not self.cita and not self.venta:
            raise ValidationError("Un pago debe estar asociado a una cita o a una venta.")