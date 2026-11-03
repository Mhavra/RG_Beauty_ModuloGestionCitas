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

from website import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/', views.registro_view, name='registro'),
    path('reserva/paso1/<int:servicio_id>/', views.reserva_paso1_servicios, name='reserva_paso1'),
    path('reserva/paso2/<int:servicio_id>/', views.reserva_paso2_fecha, name='reserva_paso2'),
    path('reserva/paso3/<int:servicio_id>/<int:empleado_id>/', views.reserva_paso3_horarios, name='reserva_paso3'),
    path('reserva/paso4/resumen/', views.reserva_paso4_resumen, name='reserva_paso4'),
    path('reserva/paso5/pagar/', views.reserva_paso5_procesar_pago, name='reserva_paso5'),
    path('reserva/exito/<int:cita_id>/', views.reserva_paso6_exito, name='reserva_paso6_exito'),
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),

]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)