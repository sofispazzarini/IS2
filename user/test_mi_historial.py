from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from actividad.models import Actividad
from turno.models import Clase, Reserva, Asistencia
from user.models import Profesor
from datetime import date, time, timedelta

User = get_user_model()


class MiHistorialTestCase(TestCase):
    def setUp(self):
        # Crear usuario cliente
        self.cliente = User.objects.create_user(
            username='cliente1',
            email='cliente1@test.com',
            password='test123',
            dni='12312312',
            rol='cliente'
        )

        # Profesor y actividad
        self.profesor = Profesor.objects.create(nombre='Ana', apellido='Lopez', email='ana@test.com')
        self.actividad = Actividad.objects.create(nombre='Rehabilitación', descripcion='Desc', duracion_min=60, precio=0)

        # Clase reciente y siguiente (fechas relativas para evitar validación de fecha pasada)
        hoy = date.today()
        mañana = hoy + timedelta(days=1)
        self.clase_old = Clase.objects.create(actividad=self.actividad, profesor=self.profesor, fecha=hoy, hora_inicio=time(10,0), hora_fin=time(11,0), cupo_maximo=10, salon='Sala A')
        self.clase_new = Clase.objects.create(actividad=self.actividad, profesor=self.profesor, fecha=mañana, hora_inicio=time(10,0), hora_fin=time(11,0), cupo_maximo=10, salon='Sala A')

        # Reservas y asistencia
        self.reserva_old = Reserva.objects.create(usuario=self.cliente, clase=self.clase_old, estado='asistida')
        self.asistencia_old = Asistencia.objects.create(reserva=self.reserva_old, presente=True, registrado_por=self.cliente)

        self.reserva_new = Reserva.objects.create(usuario=self.cliente, clase=self.clase_new, estado='asistida')
        self.asistencia_new = Asistencia.objects.create(reserva=self.reserva_new, presente=True, registrado_por=self.cliente)

        self.client = Client()

    def test_historial_muestra_clases_ordenadas(self):
        self.client.login(username='cliente1', password='test123')
        response = self.client.get(reverse('user:mi_historial'))
        self.assertEqual(response.status_code, 200)
        # New class must appear before old in the context queryset
        reservas = list(response.context['reservas'])
        self.assertGreater(len(reservas), 1)
        self.assertEqual(reservas[0].pk, self.reserva_new.pk)
        self.assertEqual(reservas[1].pk, self.reserva_old.pk)
        self.assertContains(response, 'Rehabilitación')

    def test_historial_vacio(self):
        # Nuevo cliente sin reservas
        cliente2 = User.objects.create_user(username='cliente2', email='cliente2@test.com', password='test123', dni='99999999', rol='cliente')
        self.client.login(username='cliente2', password='test123')
        response = self.client.get(reverse('user:mi_historial'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Aún no tienes clases registradas en tu historial')
