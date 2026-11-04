from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

from website import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Autenticación
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('registro/', views.registro_view, name='registro'),

    # Reserva (flujo público multi-paso)
    path('', views.reserva_paso1_servicios, name='reserva_paso1'),
    path('reserva/paso2/<int:servicio_id>/', views.reserva_paso2_fecha, name='reserva_paso2'),
    path('reserva/paso3/<int:servicio_id>/<int:empleado_id>/', views.reserva_paso3_horarios, name='reserva_paso3'),
    path('reserva/paso4/resumen/', views.reserva_paso4_resumen, name='reserva_paso4'),
    path('reserva/paso5/pagar/', views.reserva_paso5_procesar_pago, name='reserva_paso5'),
    path('reserva/exito/<int:cita_id>/', views.reserva_paso6_exito, name='reserva_paso6_exito'),

    # CRUD de citas
    path('mis-citas/', views.mis_citas, name='mis_citas'),
    path('mis-citas/<int:pk>/', views.detalle_cita, name='detalle_cita'),
    path('mis-citas/<int:pk>/editar/', views.editar_cita, name='editar_cita'),
    path('mis-citas/<int:pk>/eliminar/', views.eliminar_cita, name='eliminar_cita'),
    path('citas/crear/', views.crear_cita, name='crear_cita'),

    # Cuenta de usuario
    path('cuenta/', views.cuenta, name='cuenta'),
    path('cuenta/editar/', views.editar_perfil, name='editar_perfil'),
    path('cuenta/password/', views.CambiarPasswordView.as_view(), name='cambiar_password'),

    # Panel admin
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)