from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import Cita, ConfiguracionSistema, Usuario


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