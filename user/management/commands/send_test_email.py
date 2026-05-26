from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = 'Enviar un correo de prueba para verificar la configuración SMTP'

    def add_arguments(self, parser):
        parser.add_argument('--to', required=True, help='Correo destino')

    def handle(self, *args, **options):
        to = options['to']
        subject = 'SIRCA - Prueba de correo'
        message = 'Este es un correo de prueba enviado desde la aplicación SIRCA.'
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@sirca.local')

        self.stdout.write(f'Usando backend: {getattr(settings, "EMAIL_BACKEND", "(no definido)")}')
        try:
            send_mail(subject, message, from_email, [to], fail_silently=False)
            self.stdout.write(self.style.SUCCESS(f'Correo enviado a {to}'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error al enviar correo: {e}'))
