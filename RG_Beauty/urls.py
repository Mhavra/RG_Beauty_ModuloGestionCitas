"""
URL configuration for RG_Beauty project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

from website import views


urlpatterns = [
    path('', RedirectView.as_view(pattern_name='login', permanent=False), name='home'),
    
    path('admin/', admin.site.urls),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/', views.registro_view, name='registro'),
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/cita/<int:pk>/estado/', views.admin_cambiar_estado, name='admin_cambiar_estado'),
    path('reserva/paso1/', views.reserva_paso1_servicios, name='reserva_paso1'),
    path('reserva/paso2/<int:servicio_id>/', views.reserva_paso2_fecha, name='reserva_paso2'),
    path('reserva/paso3/<int:servicio_id>/<int:empleado_id>/', views.reserva_paso3_horarios, name='reserva_paso3'),
    path('reserva/paso4/resumen/', views.reserva_paso4_resumen, name='reserva_paso4'),
    path('reserva/paso5/pagar/', views.reserva_paso5_procesar_pago, name='reserva_paso5'),
    path('reserva/exito/<int:cita_id>/', views.reserva_paso6_exito, name='reserva_paso6_exito'),
    path('mis-citas/', views.mis_citas, name='mis_citas'),
    path('mis-citas/<int:pk>/', views.detalle_cita, name='detalle_cita'),
    path('mis-citas/<int:pk>/editar/', views.editar_cita, name='editar_cita'),
    path('mis-citas/<int:pk>/eliminar/', views.eliminar_cita, name='eliminar_cita'),
    path('api/verificar-disponibilidad/<int:servicio_id>/<int:empleado_id>/', views.api_verificar_disponibilidad, name='api_verificar_disponibilidad'),
    # Mi Cuenta
    path('cuenta/', views.cuenta, name='cuenta'),
    path('cuenta/editar/', views.editar_perfil, name='editar_perfil'),
    path('cuenta/password/', views.CambiarPasswordView.as_view(), name='cambiar_password'),

    # ============ PANEL DE GESTIÓN (ADMIN) ============
    # Dashboard 
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),

    # --- Citas: listado completo con filtros ---
    path('gestion/citas/', views.gestion_citas, name='gestion_citas'),

    # --- Servicios ---
    path('gestion/servicios/', views.gestion_servicios, name='gestion_servicios'),
    path('gestion/servicios/nuevo/', views.gestion_servicio_form, name='gestion_servicio_nuevo'),
    path('gestion/servicios/<int:pk>/editar/', views.gestion_servicio_form, name='gestion_servicio_editar'),
    path('gestion/servicios/<int:pk>/eliminar/', views.gestion_servicio_eliminar, name='gestion_servicio_eliminar'),

    # --- Profesionales ---
    path('gestion/profesionales/', views.gestion_profesionales, name='gestion_profesionales'),
    path('gestion/profesionales/nuevo/', views.gestion_profesional_form, name='gestion_profesional_nuevo'),
    path('gestion/profesionales/<int:pk>/editar/', views.gestion_profesional_form, name='gestion_profesional_editar'),

    # --- Disponibilidad semanal ---
    path('gestion/disponibilidad/', views.gestion_disponibilidad, name='gestion_disponibilidad'),
    path('gestion/disponibilidad/nueva/', views.gestion_disponibilidad_form, name='gestion_disponibilidad_nueva'),
    path('gestion/disponibilidad/<int:pk>/editar/', views.gestion_disponibilidad_form, name='gestion_disponibilidad_editar'),
    path('gestion/disponibilidad/<int:pk>/eliminar/', views.gestion_disponibilidad_eliminar, name='gestion_disponibilidad_eliminar'),

    # --- Bloqueos de horario ---
    path('gestion/bloqueos/', views.gestion_bloqueos, name='gestion_bloqueos'),
    path('gestion/bloqueos/nuevo/', views.gestion_bloqueo_form, name='gestion_bloqueo_nuevo'),
    path('gestion/bloqueos/<int:pk>/editar/', views.gestion_bloqueo_form, name='gestion_bloqueo_editar'),
    path('gestion/bloqueos/<int:pk>/eliminar/', views.gestion_bloqueo_eliminar, name='gestion_bloqueo_eliminar'),

    # --- Pagos ---
    path('gestion/pagos/', views.gestion_pagos, name='gestion_pagos'),

    # --- Configuración del sistema ---
    path('gestion/configuracion/', views.gestion_configuracion, name='gestion_configuracion'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)