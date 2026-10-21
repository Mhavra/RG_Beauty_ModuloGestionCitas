# RG_Beauty_ModuloGestionCitas


Proyecto Django de ejemplo.

## Requisitos previos

- Python 3.9+
- MySQL instalado y en ejecución

> **Importante:** 
> ```sql
> CREATE DATABASE ;
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