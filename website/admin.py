from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Usuario, 
    ConfiguracionSistema, 
    Servicio, 
    Disponibilidad, 
    BloqueoHorario, 
    Cita, 
    CitaServicio, 
    Pago
)

# ==========================================
# 1. USUARIOS
# ==========================================
@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    # Añadimos los campos personalizados a la vista de edición de usuarios
    fieldsets = UserAdmin.fieldsets + (
        ('Información del Salón', {'fields': ('rol', 'telefono')}),
    )
    # Añadimos los campos a la vista de creación de usuarios
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información del Salón', {'fields': ('rol', 'telefono', 'email')}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'rol', 'telefono', 'is_active')
    list_filter = ('rol', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'telefono')


# ==========================================
# 2. CONFIGURACIÓN DEL SISTEMA
# ==========================================
@admin.register(ConfiguracionSistema)
class ConfiguracionSistemaAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'porcentaje_abono', 'permite_monto_fijo', 'monto_fijo_abono', 'ultima_modificacion')
    
    # Evitar que se creen múltiples configuraciones. Solo debe haber una.
    def has_add_permission(self, request):
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)


# ==========================================
# 3. SERVICIOS
# ==========================================
@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ('nombre_serv', 'duracion_minutos', 'precio_serv')
    search_fields = ('nombre_serv',)
    list_filter = ('duracion_minutos',)


# ==========================================
# 4. DISPONIBILIDAD Y BLOQUEOS
# ==========================================
@admin.register(Disponibilidad)
class DisponibilidadAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'dia_semana', 'hora_inicio', 'hora_fin')
    list_filter = ('empleado', 'dia_semana')
    search_fields = ('empleado__first_name', 'empleado__last_name')

@admin.register(BloqueoHorario)
class BloqueoHorarioAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'fecha_inicio', 'fecha_fin', 'motivo')
    list_filter = ('empleado', 'fecha_inicio', 'fecha_fin')
    search_fields = ('empleado__first_name', 'empleado__last_name', 'motivo')


# ==========================================
# 5. PAGOS (Inline para verlos dentro de la Cita)
# ==========================================
class PagoInline(admin.TabularInline):
    model = Pago
    extra = 0 # No mostrar formularios vacíos extra por defecto
    readonly_fields = ('fecha_pago',)
    fields = ('monto', 'metodo_pago', 'tipo_pago', 'estado', 'transaccion_id', 'fecha_pago')


# ==========================================
# 6. CITAS (El corazón del sistema)
# ==========================================
class CitaServicioInline(admin.TabularInline):
    model = CitaServicio
    extra = 1

@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = (
        'id', 
        'fecha_hora_cita', 
        'cliente', 
        'empleado', 
        'estado', 
        'estado_abono', 
        'monto_abono'
    )
    list_filter = ('estado', 'estado_abono', 'fecha_hora_cita', 'empleado')
    search_fields = (
        'cliente__first_name', 
        'cliente__last_name', 
        'cliente__telefono',
        'empleado__first_name', 
        'empleado__last_name'
    )
    date_hierarchy = 'fecha_hora_cita' # Navegación rápida por fechas arriba a la derecha
    inlines = [CitaServicioInline, PagoInline]
    
    # Organización del formulario de la Cita
    fieldsets = (
        ('Información Principal', {
            'fields': ('cliente', 'empleado', 'fecha_hora_cita', 'estado')
        }),
        ('Información del Abono', {
            'fields': ('monto_abono', 'estado_abono')
        }),
        ('Notificaciones', {
            'fields': ('historial_notificaciones',),
            'classes': ('collapse',) # Oculto por defecto para no hacer ruido visual
        }),
    )
    
    readonly_fields = ('historial_notificaciones',)


# ==========================================
# 7. PAGOS (Registro independiente)
# ==========================================
@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha_pago', 'cliente', 'monto', 'metodo_pago', 'tipo_pago', 'estado', 'cita')
    list_filter = ('estado', 'metodo_pago', 'tipo_pago', 'fecha_pago')
    search_fields = ('cliente__first_name', 'cliente__last_name', 'transaccion_id', 'cita__id')
    date_hierarchy = 'fecha_pago'
    readonly_fields = ('fecha_pago', 'transaccion_id')