# RG_Beauty_ModuloGestionCitas
Integrantes:
Nayaret Larrondo
Lenin Moreno
Fram Salinas
Francisco Urquieta 

Aplicacion web desarrollada en Django (Python) y MySQL para la gestión de citas de la empresa RG Beauty Spa. El sistema permite a los clientes registrarse, visualizar servicios, agendar citas validando la disponibilidad real del profesional, y gestionar sus reservas. Incluye un panel de administración personalizado para la dueña del salón, control de estados de citas y registro de pagos/abonos.

## Requisitos previos

- Python 3.9+
- MySQL instalado y en ejecución

> **Importante:** 
> ```sql
> CREATE DATABASE rg_beauty_DB;
> ```

## Crear el entorno virtual

```bash
python -m venv env
```

## Activar el entorno virtual

### Linux / macOS

```bash
source env/bin/activate
```

### Windows (cmd)

```bat
env\Scripts\activate
```

### Windows (PowerShell)

```powershell
env\Scripts\Activate.ps1
```

## Instalar dependencias

Con el entorno virtual activado:

```bash
pip install -r requirements.txt
```

## Ejecutar el proyecto

```bash
python manage.py migrate
python manage.py runserver
```



Configurar la base de datos en RG_Beauty/settings.py (usuario, contraseña y nombre de la BD en MySQL).

Ejecutar migraciones: python manage.py makemigrations y python manage.py migrate

Crear superusuario: python manage.py createsuperuser

Correr el servidor: python manage.py runserver

## Declaración de Uso de Inteligencia Artificial (Criterio C2)

Como equipo declaramos el uso de herramientas de IA (Deepseek y Gemini) como asistentes de desarrollo, no como generador automático del proyecto. La arquitectura, los modelos de la base de datos, la lógica del negocio y las vistas fueron diseñadas y estructuradas por el equipo.

La IA fue utilizada específicamente en las siguientes áreas de resolución de problemas y optimización:

1. Resolución de errores críticos y configuración

Problema: Al intentar agendar, Django lanzaba errores tipo can't compare offset-naive and offset-aware datetimes y problemas con las tablas de zonas horarias de MySQL (un horario a las 13:00 se guardaba como 10:00)

Uso de IA: se consultó a la IA para entender como funcionaba USE_TZ y la conversión de horas con timezone.localtime().

Aplicación propia: El equipo implementó la logica para convertir las fechas a formato "naive" (sin zona horaria) y filtrar los solapamientos en Python antes de interactuar con la base de datos, evitando así el error de MySQL.


Problema: Error de tipos Decimal y float (dia anterior al la ultima Revisión) al calcular el abono en porcentaje.

Aplicación propia: Se aplicó la correción sugerida convirtiendo el porcentaje a Decimal() para mantener la presición financiera. También se aplicó una regla para el decimal, debido a que en settings se cambio la configuración del idioma por lo que arrojaba error por utilizar el . en decimal (en español es ,)

2. Lógica avanzada (calculo de disponibilidad)

Problema: El sistema debía evitar que dos clientes reservaran el mismo bloque si un servicio duraba más de 30 minutos.

Uso de IA: Se utilizó la IA para diseñar el algoritmo de solapamiento de intervalos de tiempo (La lógica matematica de if hora_candidata < fin_ocupaod and fin_candidato > iniciar_ocupado)

Aplicación propia: El equipo integró esta lógica en la función reutilizable (calcular_horarios_disponibles) y adaptó para que cconsiderara los bloqueos de agenda (colación, vacaciones) y los tiempos variables de cada servicio

3. Optimización de consultas (prevención del problema n+1)

Uso de IA: Se consultó como optimizar las vistas del listado (mis_citas y admin_dashboard)

Aplicación propia: El equipo implementó el uso de select_related() y prefetch_related() en las consultas ORM de DJango para atraer clientes, empleados y servicios en una sola consulta, mejorando el rendimiento

4. Interfaz de Usuario (Frontend/CSS)

Uso de IA: Se utilizó la IA para traducir el diseño visual (protipo de Figma) a código CSS puro (variables, flexbox, grid)

Aplicación propia: El equipo limpio todo el código HTML (eliminando estilos en línea y clases de Tailwind) y centralizó el diseño en un solo archivo styles.css estructurado por secciónes (botones, tarjetas, formularios, layout, etc)

5. Validaciones y Seguridad

Uso de IA: Consulta sobre cómo estructurar validaciones personalizadas en forms.py

Aplicacion propia: El equipo escribió las validaciones en EditarPerfilForm (para evitar correos duplicados) y las reglas de negocio en CitaForm (bloquear la edicion de la cita si falta menos de 1 dia).

6. Creación de API interna y asincronia (validacion en tiempo real)

Problema: Queriamos evitar que el usuario avanzara al paso 3 si no habia horarios disponibles, pero al hacerlo recargando la página (redirección normal de Django) empeoraba la experiencia del usuario. Ya que de igual forma dejaba acceder a esta y podia pagar sin tener una hora.

Aplicación propia: El equipo diseño la ruta api_verificar_disponibilidad en urls.py y programó la vista para que devuelva un JsonResponse con un booleano (disponible) y la cantidad de cupos (count)

Integración: Se escribio el código JavaScript en reserva_paso2_fecha.html para hacer el fetch a esta API. deshabilitar el botón de "Ver Horarios" mientras consulta y mostrar una alerta si la respuesta es negativa. Esto demuestra la integracion de backend y frontend de forma asincrona. Además con la anterior aplicacion mencionada, aun si el usuario desea entrar, al no tener un horario seleccionado no podria pasar al siguiente paso.

7. Seguridad, Permisos y privacidad (validación de autorización)

Problema: En un sistema de reservas, no basta con que el usuario esté logueado; un cliente nodebe poder ver ni editar la cita de otro cliente cambiando el ID en la URL

Uso de IA: Se consulto la diferencia entre autenticacióin (estar logueado) y la autorización (tener permisos), y como aplicar la regla a nivel de vista y no solo ocultando botones en el HTML.

Aplicación Propia: El equipo implemento validaciones estrictas en las vistas de detalle, edicion y eliminacion usuando if cita.cliente != request.user: raise PemrissionDenied. Esto asegura que aunque un usuario malintencionado escriba la URL .../mis-citas/5/editar/, el sistema le devuelva un error 403 (prohibido) si esta cita no le pertenece

Protección de Vistas: todas las vistas sensibles (reservas, cuenta, panel, admin) estan protegidas con el decorador @login_required.

8. Integridad de Datos y Borrado lógico

problema: si la dueña delk salon elimina un servicio o un cliente, noqueremos que se borren las citas o los pagos historicos de la base de datos.

Uso de ia: Se consultó sobre las opciones de on_delete en Django para proteger la información financiera

Aplicación propia: en los modelos de cita y pago, el equipo configuro las crelaciones con on_delete=models.RESTRICT. además en la vista de "eliminar cita", en lugar de borrar el registro de la base de datos (.delete()) se implemento un borrrado logico, cambiando el estado de la cita a 'cancelada'.
Esto preserva el historial de pagos y la trazabilidad para los reportes del negocio.

9. Pruebas de seguridad y cassos borde

En algun momenbto el equipo penso que habria probado todos los fallos posibles / ataques al sistema, por lo que se le consultó a la IA por ideas para probar fallos, cosa que nos ayudo a detectar algunos fallos que pasamos por alto en el manejo de seguridad.

10. Errores que no lograbamos encontrar

De vez en cuando se nos pasaron algunos Misstypo en la creacion del proyecto, en views o models e incluso aveces en HTML, por lo que cuando no se podia encontrar solución a estos errores se le consultaba a la IA.

(EJEMPLOS DE PROMPTS)

Tengo un problema con las fechas en Django. ME tira el error "cant't compare offset-naiveand offset-awarte datetimes" (error de consola/pagina enviado) cuando intento comparar la fecha de la BD con una que creo en Python y aparte me esta tirando un TypeError por multiplicar un float con un Decimal al calcular el abono. No quiero desactivar el USE_TZ porque tengo entendido que es una mala practica, pero necesito que las horas cuadren y que el cobro sea exacto.

Necesito que me ayudes con un algoritmo para la agenta. Los servicios duran distinto, algunos 90 min o mas y tengo que evitar que puedan reservar si se cruza con otra cita o si tiene algun bloqueo de colación

Necesito que la pagina no se recargue cuando el usuario elige la fecha, y si no hay cupos debería salir un alert en vez de mandarlo a la pantalla de error (en este caso por mas que se modifico el codigo seguia dejando entrar a la parte de pago)



Nota Ética: Todo código sugerido por la IA fue revisado, adaptado y probado por el equipo. Podemos explicar, ubicar y modificar en vivo las lineas.


