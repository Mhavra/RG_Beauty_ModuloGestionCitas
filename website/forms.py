from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import Cita, ConfiguracionSistema, Usuario, Servicio, CitaServicio

class RegistroClienteForm(UserCreationForm):
  first_name = forms.CharField(
      label='Nombre',
      max_length=50,
      widget=forms.TextInput(attrs={'class': 'form-input'}),
  )
  last_name = forms.CharField(
      label='Apellido',
      max_length=50,
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
    """Formulario para que el cliente edite TODOS los datos de su cita."""
    class Meta:
        model = Cita
        fields = ['empleado', 'servicios', 'fecha_hora_cita', 'estado', 'monto_abono', 'estado_abono']
        widgets = {
            'empleado': forms.Select(attrs={'class': 'form-input'}),
            'servicios': forms.CheckboxSelectMultiple(),
            'fecha_hora_cita': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-input'},
                format='%Y-%m-%dT%H:%M'
            ),
            'estado': forms.Select(attrs={'class': 'form-input'}),
            'monto_abono': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'estado_abono': forms.Select(attrs={'class': 'form-input'}),
        }
        labels = {
            'empleado': 'Profesional',
            'servicios': 'Servicios',
            'fecha_hora_cita': 'Fecha y hora',
            'estado': 'Estado de la cita',
            'monto_abono': 'Monto del abono (CLP)',
            'estado_abono': 'Estado del abono',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['empleado'].queryset = Usuario.objects.filter(
            rol__in=['admin', 'profesional', 'estilista']
        ).order_by('first_name')
        self.fields['servicios'].queryset = Servicio.objects.all().order_by('nombre_serv')
        # Convertir la fecha a hora local para que el input datetime-local la muestre bien
        if self.instance and self.instance.pk and 'fecha_hora_cita' in self.initial:
            from django.utils import timezone
            dt = self.initial['fecha_hora_cita']
            if timezone.is_aware(dt):
                self.initial['fecha_hora_cita'] = timezone.localtime(dt)

    def save(self, commit=True):
        cita = super().save(commit=False)
        if commit:
            cita.save()
            # Manejar M2M a través de la tabla intermedia manualmente
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
