# Configurar Gmail SMTP para SIRCA

Para enviar correos reales (por ejemplo: la contraseña temporal que genera el secretario), sigue estos pasos:

1) Habilitar 2FA y generar App Password
- Entra en tu cuenta Google: https://myaccount.google.com/security
- Activa "Verificación en dos pasos" (2FA) si no lo está.
- En "App passwords" genera una contraseña de aplicación (elige "Mail" / "Other (Custom name)").
- Copia la contraseña (será una cadena de 16 caracteres).

2) Configurar las variables de entorno
En el servidor (o en tu entorno local) define las variables de entorno que `config/settings.py` ya lee:

- `EMAIL_HOST_USER` -> tu cuenta Gmail (ej: `tucorreo@gmail.com`)
- `EMAIL_HOST_PASSWORD` -> la App Password generada
- `EMAIL_HOST` -> `smtp.gmail.com` (opcional)
- `EMAIL_PORT` -> `587` (opcional)
- `EMAIL_USE_TLS` -> `True` (opcional)
- `DEFAULT_FROM_EMAIL` -> dirección desde la que se envían los correos

Ejemplos:

- Linux / macOS (bash):

```bash
export EMAIL_HOST_USER="tucorreo@gmail.com"
export EMAIL_HOST_PASSWORD="app-password-aqui"
export DEFAULT_FROM_EMAIL="no-reply@tudominio.com"
```

- Windows (PowerShell):

```powershell
setx EMAIL_HOST_USER "tucorreo@gmail.com"
setx EMAIL_HOST_PASSWORD "app-password-aqui"
setx DEFAULT_FROM_EMAIL "no-reply@tudominio.com"
```

3) Reiniciar la aplicación
Después de definir las variables, reinicia el servidor Django para que lea las variables de entorno.

4) Prueba de envío (Django shell)

```bash
python manage.py shell -c "from django.core.mail import send_mail; send_mail('Prueba','Cuerpo','no-reply@tudominio.com',['destino@ejemplo.com'], fail_silently=False)"
```

Si el correo se envía, la configuración está correcta. Si falla, revisa el error en consola: comúnmente indica credenciales incorrectas o bloqueo por seguridad en la cuenta Google.

Notas importantes
- Gmail no permite ya el acceso de aplicaciones menos seguras. La opción válida es usar App Passwords (cuenta con 2FA).
- No guardes `EMAIL_HOST_PASSWORD` en el repositorio. Usa variables de entorno o servicios de secret management.
- Para producció n considera proveedores de envío (SendGrid, Mailgun) si necesitas mayor fiabilidad y métricas.

Cómo probar desde la UI
- En la interfaz de SIRCA, usa la función de Secretario → "Enviar contraseña temporal" a un cliente. El código usa `settings.DEFAULT_FROM_EMAIL` y `send_mail(...)`.
- Observa los logs del servidor para confirmar que `send_mail` no lanzó excepciones.
