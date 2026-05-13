from django.core.management.base import BaseCommand
from user.models import User


class Command(BaseCommand):
    help = 'Crea un usuario administrador (secretario o dueño)'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email del usuario')
        parser.add_argument('password', type=str, help='Contraseña')
        parser.add_argument(
            '--rol',
            type=str,
            default='secretario',
            choices=['secretario', 'dueno'],
            help='Rol del usuario (secretario o dueno)'
        )
        parser.add_argument('--nombre', type=str, default='Admin', help='Nombre')
        parser.add_argument('--apellido', type=str, default='Usuario', help='Apellido')
        parser.add_argument('--dni', type=str, default='00000000', help='DNI')

    def handle(self, *args, **options):
        email = options['email']
        password = options['password']
        rol = options['rol']

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f'Ya existe un usuario con email {email}'))
            user = User.objects.get(email=email)
            user.rol = rol
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Rol actualizado a: {rol}'))
            return

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=options['nombre'],
            last_name=options['apellido'],
            dni=options['dni'],
            telefono='0000000000',
            rol=rol,
        )

        self.stdout.write(self.style.SUCCESS(
            f'Usuario creado exitosamente:\n'
            f'  Email: {email}\n'
            f'  Rol: {rol}\n'
            f'  Password: {password}'
        ))
