from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils import timezone
from .models import Cita, ConfiguracionSistema, Usuario, Servicio


class RegistroClienteForm(UserCreationForm):
    first_name = forms.CharField(label='Nombre', max_length=50, widget=forms.TextInput(attrs={'class': 'form-input w-full border rounded-lg p-2 text-sm'}))
    last_name = forms.CharField(label='Apellido', max_length=50, widget=forms.TextInput(attrs={'class': 'form-input w-full border rounded-lg p-2 text-sm'}))
    email = forms.EmailField(label='Correo Electrónico', widget=forms.EmailInput(attrs={'class': 'form-input w-full border rounded-lg p-2 text-sm'}))
    telefono = forms.CharField(
        label='Teléfono (+569)',
        max_length=12,
        widget=forms.TextInput(attrs={'placeholder': '+56912345678', 'class': 'form-input w-full border rounded-lg p-2 text-sm'}),
    )

    class Meta:
        model = Usuario
        fields = ('first_name', 'last_name', 'email', 'telefono')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.rol = 'cliente'
        if commit:
            user.save()
        return user

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ya existe una cuenta registrada con este correo.')
        return email


class LoginForm(AuthenticationForm):
    username = forms.EmailField(label='Correo Electrónico', widget=forms.EmailInput(attrs={'class': 'form-input w-full border rounded-lg p-2 text-sm'}))
    password = forms.CharField(label='Contraseña', widget=forms.PasswordInput(attrs={'class': 'form-input w-full border rounded-lg p-2 text-sm'}))


class FiltroReporteForm(forms.Form):
    fecha_inicio = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}))
    fecha_fin = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}))
    formato = forms.ChoiceField(
        choices=[('pdf', 'Exportar PDF'), ('excel', 'Exportar Excel (.xlsx)')],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )


class CitaForm(forms.ModelForm):
    """
    ModelForm para crear/editar Citas.
    A2 - Formulario ligado al modelo con labels, help_texts, widgets y validación propia.
    """
    class Meta:
        model = Cita
        fields = ['cliente', 'empleado', 'fecha_hora_cita', 'estado', 'servicios']
        widgets = {
            'fecha_hora_cita': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'w-full border rounded-lg p-2 text-sm'}),
            'cliente': forms.Select(attrs={'class': 'w-full border rounded-lg p-2 text-sm'}),
            'empleado': forms.Select(attrs={'class': 'w-full border rounded-lg p-2 text-sm'}),
            'estado': forms.Select(attrs={'class': 'w-full border rounded-lg p-2 text-sm'}),
            'servicios': forms.CheckboxSelectMultiple(),
        }
        labels = {
            'cliente': 'Cliente',
            'empleado': 'Profesional que atiende',
            'fecha_hora_cita': 'Fecha y hora de la cita',
            'estado': 'Estado de la cita',
            'servicios': 'Servicios reservados',
        }
        help_texts = {
            'fecha_hora_cita': 'Debe ser una fecha futura.',
            'servicios': 'Puedes seleccionar más de un servicio.',
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['empleado'].queryset = Usuario.objects.filter(
            rol__in=['admin', 'profesional', 'estilista']
        ).order_by('first_name')
        self.fields['servicios'].queryset = Servicio.objects.order_by('nombre_serv')
        self.fields['cliente'].queryset = Usuario.objects.filter(rol='cliente').order_by('first_name')
        # Cliente no puede cambiar el dueño de la cita
        if user is not None and user.rol == 'cliente':
            self.fields['cliente'].disabled = True
            self.fields['cliente'].initial = user
            self.fields['cliente'].queryset = Usuario.objects.filter(pk=user.pk)

    def clean_fecha_hora_cita(self):
        fecha = self.cleaned_data['fecha_hora_cita']
        if fecha < timezone.now():
            raise forms.ValidationError('La fecha y hora de la cita no puede estar en el pasado.')
        return fecha


class EditarPerfilForm(forms.ModelForm):
    """
    A8 - Edición de datos de la cuenta con validación de correo único.
    """
    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'email', 'telefono']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'w-full border rounded-lg p-2 text-sm'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full border rounded-lg p-2 text-sm'}),
            'email': forms.EmailInput(attrs={'class': 'w-full border rounded-lg p-2 text-sm'}),
            'telefono': forms.TextInput(attrs={'class': 'w-full border rounded-lg p-2 text-sm'}),
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
            raise forms.ValidationError('Este correo ya pertenece a otra cuenta.')
        return email