from django import forms
import datetime
from django.utils import timezone
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import Cita, ConfiguracionSistema, Usuario, Servicio, CitaServicio
from .models import Servicio, Usuario, Disponibilidad, BloqueoHorario, ConfiguracionSistema
from django.core.validators import RegexValidator


validador_letras = RegexValidator(
    regex=r'^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$',
    message='Este campo solo puede contener letras y espacios. No se permiten números ni caracteres especiales.'
)

class RegistroClienteForm(UserCreationForm):
    first_name = forms.CharField(
        label='Nombre',
        max_length=50,
        validators=[validador_letras],
        widget=forms.TextInput(attrs={'class': 'form-input'}),
    )
    last_name = forms.CharField(
        label='Apellido',
        max_length=50,
        validators=[validador_letras],
        widget=forms.TextInput(attrs={'class': 'form-input'}),
    )
    rut = forms.CharField(
        label='RUT',
        max_length=12,
        widget=forms.TextInput(attrs={'class': 'form-input'}),
    )
    email = forms.EmailField(
        label='Correo Electrónico',
        widget=forms.EmailInput(attrs={'class': 'form-input'}),
    )
    telefono = forms.CharField(
        label='Teléfono (+569)',
        max_length=12,
        widget=forms.TextInput(
            attrs={'placeholder': '+56912345678', 'class': 'form-input'}
        ),
    )

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Este correo ya está registrado. Por favor, usa otro o inicia sesión.')
        return email

    class Meta:
        model = Usuario
        fields = ('first_name', 'last_name', 'rut' ,'email', 'telefono')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.rol = 'cliente'
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label='Correo Electrónico',
        widget=forms.EmailInput(attrs={'class': 'form-input'}),
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-input'}),
    )


class FiltroReporteForm(forms.Form):
    fecha_inicio = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'})
    )
    fecha_fin = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'})
    )
    formato = forms.ChoiceField(
        choices=[
            ('pdf', 'Exportar PDF'),
            ('excel', 'Exportar Excel (.xlsx)'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

#agregado para que el cliente pueda editar su cita

class CitaForm(forms.ModelForm):
    """Formulario para que el cliente edite su cita con reglas de negocio."""
    class Meta:
        model = Cita
        # ELIMINAMOS 'estado' de aquí
        fields = ['empleado', 'servicios', 'fecha_hora_cita', 'monto_abono', 'estado_abono']
        widgets = {
            'empleado': forms.Select(attrs={'class': 'form-input'}),
            'servicios': forms.CheckboxSelectMultiple(),
            'fecha_hora_cita': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-input'},
                format='%Y-%m-%dT%H:%M'
            ),
            'monto_abono': forms.NumberInput(attrs={'class': 'form-input'}),
            'estado_abono': forms.Select(attrs={'class': 'form-input'}),
        }
        labels = {
            'empleado': 'Profesional',
            'servicios': 'Servicios',
            'fecha_hora_cita': 'Fecha y hora',
            'monto_abono': 'Monto del abono (CLP)',
            'estado_abono': 'Estado del abono',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['empleado'].queryset = Usuario.objects.filter(
            rol__in=['admin', 'profesional', 'estilista']
        ).order_by('first_name')
        self.fields['servicios'].queryset = Servicio.objects.all().order_by('nombre_serv')

        self.fields['monto_abono'].disabled = True
        self.fields['estado_abono'].disabled = True

        # (El resto de tu lógica de 1 día de anticipación se mantiene igual)
        if self.instance and self.instance.pk:
            ahora = timezone.now()
            if self.instance.fecha_hora_cita <= ahora + datetime.timedelta(days=1):
                self.fields['fecha_hora_cita'].disabled = True
                self.fields['empleado'].disabled = True
                self.fields['servicios'].disabled = True
                self.fields['fecha_hora_cita'].help_text = "⚠️ No puedes modificar la fecha, profesional o servicios con menos de 1 día de anticipación."

            if 'fecha_hora_cita' in self.initial:
                dt = self.initial['fecha_hora_cita']
                if timezone.is_aware(dt):
                    self.initial['fecha_hora_cita'] = timezone.localtime(dt)

    def save(self, commit=True):
        cita = super().save(commit=False)
        if commit:
            cita.save()
            if not self.fields['servicios'].disabled:
                CitaServicio.objects.filter(cita=cita).delete()
                for servicio in self.cleaned_data.get('servicios', []):
                    CitaServicio.objects.create(cita=cita, servicio=servicio)
        return cita

class EditarPerfilForm(forms.ModelForm):
    """Formulario para editar los datos del perfil. NO incluye rol."""
    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'email', 'telefono']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'telefono': forms.TextInput(attrs={'class': 'form-input'}),
        }
        labels = {
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'email': 'Correo Electrónico',
            'telefono': 'Teléfono',
        }

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if Usuario.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Este correo ya está registrado por otra persona.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']  # Mantener username sincronizado con email
        if commit:
            user.save()
        return user

class ServicioForm(forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ['nombre_serv', 'duracion_minutos', 'precio_serv', 'imagen']
        widgets = {
            'nombre_serv': forms.TextInput(attrs={'class': 'form-input'}),
            'duracion_minutos': forms.NumberInput(attrs={'class': 'form-input', 'min': 15, 'step': 15}),
            'precio_serv': forms.NumberInput(attrs={'class': 'form-input', 'min': 0, 'step': 1000}),
        }
        error_messages = {
            'nombre_serv': {
                'unique': 'Ya existe un servicio con este nombre. Por favor, elige otro.',
            }
        }

class ProfesionalForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input'}),
        required=False,
        label='Contraseña',
        help_text='Dejar vacío para no cambiar la contraseña.'
    )

    servicios_asignados = forms.ModelMultipleChoiceField(
        queryset=Servicio.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'checkbox-list'}),
        required=False,
        label="Servicios que ofrece este profesional"
    )
    
    class Meta:
        model = Usuario
        # SE AGREGA 'servicios_asignados' AQUI
        fields = ['username', 'first_name', 'last_name', 'email', 'telefono', 'rol', 'servicios_asignados']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'telefono': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+56912345678'}),
            'rol': forms.Select(attrs={'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rol'].choices = [
            ('profesional', 'Profesional'),
            ('admin', 'Administradora'),
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        pwd = self.cleaned_data.get('password')
        if pwd:
            user.set_password(pwd)
        elif not user.pk:
            user.set_unusable_password()
        if commit:
            user.save()
            self.save_m2m() # <-- IMPORTANTE: Guarda los servicios
        return user

class DisponibilidadForm(forms.ModelForm):
    class Meta:
        model = Disponibilidad
        fields = ['empleado', 'dia_semana', 'hora_inicio', 'hora_fin']
        widgets = {
            'empleado': forms.Select(attrs={'class': 'form-input'}),
            'dia_semana': forms.Select(attrs={'class': 'form-input'}),
            'hora_inicio': forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
            'hora_fin': forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
        }

class BloqueoForm(forms.ModelForm):
    class Meta:
        model = BloqueoHorario
        fields = ['empleado', 'fecha_inicio', 'fecha_fin', 'motivo']
        widgets = {
            'empleado': forms.Select(attrs={'class': 'form-input'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'motivo': forms.TextInput(attrs={'class': 'form-input'}),
        }

class ConfiguracionForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionSistema
        fields = ['porcentaje_abono', 'permite_monto_fijo', 'monto_fijo_abono']
        widgets = {
            'porcentaje_abono': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': 0, 'max': 100}),
            'monto_fijo_abono': forms.NumberInput(attrs={'class': 'form-input', 'step': '100', 'min': 0}),
        }

