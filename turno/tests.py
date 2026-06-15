from datetime import date, time, timedelta, datetime as dt, timezone as dt_tz
from django.test import TestCase, override_settings
from django.utils import timezone
from unittest.mock import patch

from user.models import User, Profesor
from actividad.models import Actividad
from turno.models import Clase, Reserva, Asistencia
from turno.services import validar_qr


@override_settings(USE_TZ=False)
class ValidarQRTestCase(TestCase):
    """Tests para validación de QR según criterios de aceptación RF."""

    def setUp(self):
        self.usuario = User.objects.create_user(
            username='cliente1',
            email='cliente@test.com',
            password='test123',
            dni='12345678',
            rol='cliente'
        )
        self.admin = User.objects.create_user(
            username='admin1',
            email='admin@test.com',
            password='test123',
            dni='87654321',
            rol='secretario'
        )
        self.profesor = Profesor.objects.create(
            nombre='Juan',
            apellido='Perez',
            email='prof@test.com'
        )
        self.actividad = Actividad.objects.create(
            nombre='Yoga',
            descripcion='Clase de yoga',
            duracion_min=60,
            precio=1000
        )

    def _crear_clase(self, fecha, hora_inicio, hora_fin):
        return Clase.objects.create(
            actividad=self.actividad,
            profesor=self.profesor,
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            cupo_maximo=10,
            salon='Sala A'
        )

    def _crear_reserva(self, clase, qr_usado=False):
        return Reserva.objects.create(
            usuario=self.usuario,
            clase=clase,
            estado='confirmada',
            qr_usado=qr_usado
        )

    @patch('turno.services.timezone.now')
    @patch('turno.services.timezone.localtime')
    def test_escenario_1_registro_exitoso(self, mock_localtime, mock_now):
        """
        Escenario I: Registro exitoso
        Dada la fecha actual 10/10/04 a las 9:50 am, un QR sin usar
        para una clase en la fecha actual a las 10:00 am.
        Cuando el usuario muestra el QR en el lector.
        Entonces el sistema registra el presente y deshabilita el QR.
        """
        fecha_clase = date(2004, 10, 10)
        fake_now = dt(2004, 10, 10, 9, 50)
        mock_now.return_value = fake_now
        mock_localtime.return_value = fake_now

        clase = self._crear_clase(
            fecha=fecha_clase,
            hora_inicio=time(10, 0),
            hora_fin=time(11, 0)
        )
        reserva = self._crear_reserva(clase, qr_usado=False)

        resultado = validar_qr(str(reserva.qr_uuid), registrado_por=self.admin)

        self.assertTrue(resultado.exito)
        self.assertIn('exitoso', resultado.mensaje.lower())

        reserva.refresh_from_db()
        self.assertTrue(reserva.qr_usado)
        self.assertEqual(reserva.estado, 'asistida')
        self.assertTrue(Asistencia.objects.filter(reserva=reserva).exists())

    @patch('turno.services.timezone.now')
    @patch('turno.services.timezone.localtime')
    def test_escenario_2_qr_vencido_fecha_pasada(self, mock_localtime, mock_now):
        """
        Escenario II: Registro fallido por QR vencido
        Dada la fecha actual 11/10/04 a las 9:50 am, un QR sin usar
        para una clase del 10/10/04 a las 10:00 am.
        Cuando el usuario muestra el QR en el lector.
        Entonces el sistema informa mensaje de error por QR vencido.
        """
        fecha_clase = date(2004, 10, 10)
        fake_now = dt(2004, 10, 11, 9, 50)
        mock_now.return_value = fake_now
        mock_localtime.return_value = fake_now

        clase = self._crear_clase(
            fecha=fecha_clase,
            hora_inicio=time(10, 0),
            hora_fin=time(11, 0)
        )
        reserva = self._crear_reserva(clase, qr_usado=False)

        resultado = validar_qr(str(reserva.qr_uuid), registrado_por=self.admin)

        self.assertFalse(resultado.exito)
        self.assertIn('vencido', resultado.mensaje.lower())

        reserva.refresh_from_db()
        self.assertFalse(reserva.qr_usado)

    @patch('turno.services.timezone.now')
    @patch('turno.services.timezone.localtime')
    def test_escenario_3_qr_ya_usado(self, mock_localtime, mock_now):
        """
        Escenario III: Registro fallido por QR usado
        Dada la fecha actual 10/10/04 a las 9:50 am, un QR usado
        para una clase en la fecha actual a las 10:00 am.
        Cuando el usuario muestra el QR en el lector.
        Entonces el sistema informa error por QR deshabilitado.
        """
        fecha_clase = date(2004, 10, 10)
        fake_now = dt(2004, 10, 10, 9, 50)
        mock_now.return_value = fake_now
        mock_localtime.return_value = fake_now

        clase = self._crear_clase(
            fecha=fecha_clase,
            hora_inicio=time(10, 0),
            hora_fin=time(11, 0)
        )
        reserva = self._crear_reserva(clase, qr_usado=True)

        resultado = validar_qr(str(reserva.qr_uuid), registrado_por=self.admin)

        self.assertFalse(resultado.exito)
        self.assertEqual(resultado.mensaje, 'QR ya usado')

    @patch('turno.services.timezone.now')
    @patch('turno.services.timezone.localtime')
    def test_escenario_4_qr_fecha_no_habilitada(self, mock_localtime, mock_now):
        """
        Escenario IV: Registro fallido por fecha no habilitada
        Dada la fecha actual 10/10/04 a las 9:50 am, un QR sin usar
        para una clase del 15/10/04 a las 10:00 am.
        Cuando el usuario muestra el QR en el lector.
        Entonces el sistema informa error por QR no correspondiente
        a la fecha habilitada y horario actual.
        """
        fecha_clase = date(2004, 10, 15)
        fake_now = dt(2004, 10, 10, 9, 50)
        mock_now.return_value = fake_now
        mock_localtime.return_value = fake_now

        clase = self._crear_clase(
            fecha=fecha_clase,
            hora_inicio=time(10, 0),
            hora_fin=time(11, 0)
        )
        reserva = self._crear_reserva(clase, qr_usado=False)

        resultado = validar_qr(str(reserva.qr_uuid), registrado_por=self.admin)

        self.assertFalse(resultado.exito)
        self.assertIn('no habilitado', resultado.mensaje.lower())

    @patch('turno.services.timezone.now')
    @patch('turno.services.timezone.localtime')
    def test_qr_fuera_de_ventana_30_minutos(self, mock_localtime, mock_now):
        """
        Test adicional: QR mostrado más de 30 minutos antes de la clase.
        """
        fecha_clase = date(2004, 10, 10)
        fake_now = dt(2004, 10, 10, 9, 0)
        mock_now.return_value = fake_now
        mock_localtime.return_value = fake_now

        clase = self._crear_clase(
            fecha=fecha_clase,
            hora_inicio=time(10, 0),
            hora_fin=time(11, 0)
        )
        reserva = self._crear_reserva(clase, qr_usado=False)

        resultado = validar_qr(str(reserva.qr_uuid), registrado_por=self.admin)

        self.assertFalse(resultado.exito)
        self.assertIn('no habilitado', resultado.mensaje.lower())

    @patch('turno.services.timezone.now')
    @patch('turno.services.timezone.localtime')
    def test_qr_despues_fin_clase(self, mock_localtime, mock_now):
        """
        Test adicional: QR mostrado después de que terminó la clase.
        """
        fecha_clase = date(2004, 10, 10)
        fake_now = dt(2004, 10, 10, 11, 30)
        mock_now.return_value = fake_now
        mock_localtime.return_value = fake_now

        clase = self._crear_clase(
            fecha=fecha_clase,
            hora_inicio=time(10, 0),
            hora_fin=time(11, 0)
        )
        reserva = self._crear_reserva(clase, qr_usado=False)

        resultado = validar_qr(str(reserva.qr_uuid), registrado_por=self.admin)

        self.assertFalse(resultado.exito)
        self.assertIn('vencido', resultado.mensaje.lower())

    def test_qr_inexistente(self):
        """Test: UUID de QR que no existe en la base de datos."""
        resultado = validar_qr('00000000-0000-0000-0000-000000000000')

        self.assertFalse(resultado.exito)
        self.assertIn('no existe', resultado.mensaje.lower())
