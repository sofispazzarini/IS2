from dotenv import load_dotenv
import os
from pathlib import Path
load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-cambiar-esta-clave-en-produccion"

DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '.ngrok-free.dev', '.ngrok.io']

CSRF_TRUSTED_ORIGINS = [
    'https://*.ngrok-free.dev',
    'https://*.ngrok.io',
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "user",
    "actividad",
    "turno",
    "pago",
    "resena",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_USER_MODEL = 'user.User'

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es"
TIME_ZONE = "America/Argentina/Buenos_Aires"
USE_I18N = True
USE_TZ = True

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/'  # o donde quieras que vaya después de loguear
LOGOUT_REDIRECT_URL = ('/auth/login/')
# Configuración para envío de correos reales mediante Gmail
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

# Tu dirección de correo desde donde se enviarán los mensajes
EMAIL_HOST_USER = 'jm951659@gmail.com'

# TU CONTRASEÑA DE APLICACIÓN (No es tu contraseña normal de Gmail)
EMAIL_HOST_PASSWORD = 'uwop mvim hbvi sejc'

# El remitente que verán los usuarios
DEFAULT_FROM_EMAIL = 'SIRCA <jm951659@gmail.com>'

NGROK_URL = os.getenv("NGROK_URL", "http://127.0.0.1:8000")



MERCADO_PAGO_ACCESS_TOKEN = os.getenv("MERCADO_PAGO_ACCESS_TOKEN")
MERCADO_PAGO_PUBLIC_KEY = os.getenv("MERCADO_PAGO_PUBLIC_KEY")

print("TOKEN:", MERCADO_PAGO_ACCESS_TOKEN)
print("MP TOKEN =>", MERCADO_PAGO_ACCESS_TOKEN)