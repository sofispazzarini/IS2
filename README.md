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
source .venv/Scripts/activate
```

3. Instalar dependencias:

```bash
pip install -r requirements.txt
```

4. Aplicar migraciones iniciales:

```bash
python manage.py migrate
```

## Después de hacer pull/merge

Si tus compañeros actualizaron el código, corré las migraciones para sincronizar la base de datos:

```bash
pip install -r requirements.txt   # por si agregaron dependencias nuevas
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
├── core/                    # App base (home, páginas generales)
├── user/                    # Usuarios, roles y autenticación
├── actividad/               # Actividades del gimnasio
├── turno/                   # Clases, reservas, QR y asistencia
├── pago/                    # Pagos (MercadoPago, efectivo)
├── resena/                  # Reseñas de actividades
├── templates/               # Templates globales
├── static/                  # Archivos estáticos (CSS, JS)
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

## Crear usuarios administradores

Para probar funcionalidades de secretario o dueño, usar el comando `crearadmin`:

```bash
# Crear secretario
python manage.py crearadmin secretario@test.com 12345678

# Crear dueño
python manage.py crearadmin dueno@test.com 12345678 --rol=dueno

# Con datos personalizados
python manage.py crearadmin admin@sirca.com mipassword 
--rol=dueno --nombre=Juan --apellido=Perez --dni=12345678
```

Si el email ya existe, el comando actualiza el rol del usuario existente.

### Roles disponibles

| Rol | Acceso |
|-----|--------|
| `cliente` | Usuario normal (default al registrarse) |
| `secretario` | Panel de administración, gestión de clientes |
| `dueno` | Mismo acceso que secretario + futuras funcionalidades |

## Sistema de asistencia con QR

El sistema genera códigos QR únicos para cada reserva que permiten registrar asistencia.

### Cómo funciona

1. **Cliente hace una reserva** → se genera un UUID único (`qr_uuid`)
2. **Cliente paga** → la reserva pasa a estado "confirmada"
3. **30 minutos antes de la clase** → el QR se habilita y aparece en "Mis Turnos"
4. **Secretario/Dueño escanea** → el sistema valida y registra asistencia
5. **QR usado** → se deshabilita automáticamente

### Rutas importantes

| Ruta | Quién la usa | Descripción |
|------|--------------|-------------|
| `/turnos/mis-turnos/` | Cliente | Ve sus reservas y el QR cuando está habilitado |
| `/turnos/escanear-qr/` | Secretario/Dueño | Escanea QRs para registrar asistencia |

### Reglas de negocio

- El QR se habilita **30 minutos antes** de que empiece la clase
- El QR se deshabilita cuando **termina la clase** o cuando **ya fue usado**
- Solo usuarios con rol `secretario` o `dueno` pueden escanear QRs

### Dependencia

El QR usa la librería `qrcode`. Ya está en `requirements.txt`, solo hay que instalar:

```bash
pip install -r requirements.txt
```

## Siguientes pasos sugeridos

- Crear modelos en `core/models.py`.
- Agregar formularios y validaciones.
- Incorporar tests por app (`core/tests.py`).