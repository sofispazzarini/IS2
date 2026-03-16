# IS2 - Base simple de proyecto Django

Este repositorio contiene una base mínima y funcional para empezar un proyecto con Django.

## Clonar el repositorio

Si usan HTTPS:

```bash
git clone https://github.com/sofispazzarini/IS2.git
cd IS2
```

Si usan SSH:

```bash
git clone git@github.com:sofispazzarini/IS2.git
cd IS2
```

## Requisitos

- Python 3.10+ (recomendado)
- `pip`

## Instalación

1. Crear entorno virtual:

```bash
python3 -m venv .venv
```

2. Activar entorno virtual:

```bash
source .venv/bin/activate
```

3. Instalar dependencias:

```bash
pip install -r requirements.txt
```

4. Aplicar migraciones iniciales:

```bash
python manage.py migrate
```

## Ejecución

Levantar servidor de desarrollo:

```bash
python manage.py runserver
```

Abrir en navegador:

- Inicio: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/

## Arquitectura del proyecto

Estructura principal:

```text
IS2/
├── config/                  # Configuración global del proyecto Django
│   ├── settings.py          # Settings (apps, DB, middleware, templates, etc.)
│   ├── urls.py              # Enrutador principal
│   ├── asgi.py              # Entrada ASGI
│   └── wsgi.py              # Entrada WSGI
├── core/                    # App inicial del dominio
│   ├── apps.py              # Config de la app
│   ├── urls.py              # Rutas de la app
│   └── views.py             # Vistas (renderizan HTML)
├── templates/               # Templates globales
│   ├── base.html            # Plantilla base
│   └── core/home.html       # Pantalla de inicio
├── manage.py                # CLI de Django
└── requirements.txt         # Dependencias Python
```

### Flujo básico de request

1. Entra una request por una URL definida en `config/urls.py`.
2. Se deriva a la app `core` (`core/urls.py`).
3. La vista en `core/views.py` procesa y responde con `render()`.
4. Django renderiza el template `templates/core/home.html`, que extiende `templates/base.html`.

## Comandos útiles

```bash
python manage.py check
python manage.py test
python manage.py makemigrations --check
```

## Siguientes pasos sugeridos

- Crear modelos en `core/models.py`.
- Agregar formularios y validaciones.
- Incorporar tests por app (`core/tests.py`).