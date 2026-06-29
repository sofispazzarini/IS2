from datetime import date, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from user.models import User, Profesor
from actividad.models import Actividad
from turno.models import Salon, Clase, Reserva, ListaEspera


class Command(BaseCommand):
    help = 'Crea datos para probar liberación de cupo y notificación por email'

    def handle(self, *args, **options):
        self.stdout.write('=' * 60)
        self.stdout.write('SEED PARA PROBAR LIBERACIÓN DE CUPO')
        self.stdout.write('=' * 60 + '\n')

        # Usuario que va a cancelar (libera el cupo)
        usuario_cancela, created = User.objects.get_or_create(
            email='cancela@demo.com',
            defaults={
                'username': 'cancela@demo.com',
                'first_name': 'Usuario',
                'last_name': 'Cancela',
                'dni': '99000001',
                'telefono': '1199990001',
                'rol': 'cliente',
                'creditos': Decimal('5000'),
            }
        )
        if created:
            usuario_cancela.set_password('demo1234')
            usuario_cancela.save()
        self.stdout.write(f'  Usuario que cancela: cancela@demo.com / demo1234')

        # Usuario en lista de espera (TU EMAIL - recibirá la notificación)
        usuario_espera, created = User.objects.get_or_create(
            email='sofiaspazzarini@gmail.com',
            defaults={
                'username': 'sofiaspazzarini@gmail.com',
                'first_name': 'Sofia',
                'last_name': 'Spazzarini',
                'dni': '99000002',
                'telefono': '1199990002',
                'rol': 'cliente',
                'creditos': Decimal('5000'),
            }
        )
        if created:
            usuario_espera.set_password('demo1234')
            usuario_espera.save()
        self.stdout.write(f'  Usuario en espera: sofiaspazzarini@gmail.com / demo1234')

        # Usar actividad existente (Zona Media, Tren Superior o Tren Inferior)
        actividad = Actividad.objects.filter(activa=True).first()
        if not actividad:
            self.stdout.write(self.style.ERROR('No hay actividades en el sistema. Corré primero el seed principal.'))
            return

        # Usar profesor existente
        profesor = Profesor.objects.first()
        if not profesor:
            self.stdout.write(self.style.ERROR('No hay profesores en el sistema. Corré primero el seed principal.'))
            return

        # Usar salón existente
        salon = Salon.objects.first()
        if not salon:
            self.stdout.write(self.style.ERROR('No hay salones en el sistema. Corré primero el seed principal.'))
            return

        # Clase con cupo = 1 (mañana a las 10:00)
        manana = date.today() + timedelta(days=1)

        clase, created = Clase.objects.get_or_create(
            actividad=actividad,
            fecha=manana,
            hora_inicio=time(10, 0),
            defaults={
                'profesor': profesor,
                'hora_fin': time(11, 0),
                'cupo_maximo': 1,
                'salon': salon,
            }
        )
        self.stdout.write(f'\n  Clase: {actividad.nombre}')
        self.stdout.write(f'  Fecha: {manana} 10:00-11:00')
        self.stdout.write(f'  Cupo máximo: 1')

        # Reserva confirmada del usuario que va a cancelar (LLENA EL CUPO)
        reserva, created = Reserva.objects.get_or_create(
            usuario=usuario_cancela,
            clase=clase,
            defaults={
                'estado': 'confirmada',
                'monto_pagado': actividad.precio,
            }
        )
        if not created and reserva.estado != 'confirmada':
            reserva.estado = 'confirmada'
            reserva.save()
        self.stdout.write(f'  Reserva confirmada de: {usuario_cancela.email}')

        # Agregar a Sofia a la lista de espera
        espera, created = ListaEspera.objects.get_or_create(
            usuario=usuario_espera,
            clase=clase,
        )
        self.stdout.write(f'  En lista de espera: {usuario_espera.email}')

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('INSTRUCCIONES PARA PROBAR:')
        self.stdout.write('=' * 60)
        self.stdout.write('\n1. Iniciá el servidor: python manage.py runserver')
        self.stdout.write('\n2. Logueate como: cancela@demo.com / demo1234')
        self.stdout.write(f'\n3. Andá a "Mis Reservas" y cancelá la reserva de "{actividad.nombre}"')
        self.stdout.write('\n4. Revisá tu email sofiaspazzarini@gmail.com')
        self.stdout.write('   Deberías recibir un aviso de cupo liberado con link a la home')
        self.stdout.write('\n' + '=' * 60 + '\n')
