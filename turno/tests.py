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

    @patch('turno.models.timezone.localdate')
    @patch('turno.services.timezone.now')
    @patch('turno.services.timezone.localtime')
    def test_escenario_2_qr_vencido_fecha_pasada(self, mock_localtime, mock_now, mock_localdate):
        """
        Escenario II: Registro fallido por QR vencido
        Dada la fecha actual 11/10/04 a las 9:50 am, un QR sin usar
        para una clase del 10/10/04 a las 10:00 am.
        Cuando el usuario muestra el QR en el lector.
        Entonces el sistema informa mensaje de error por QR vencido.
        """
        # Primero creamos la clase cuando la fecha es 10/10/04 (mismo día de la clase)
        fecha_clase = date(2004, 10, 10)
        
        # Mockeamos localdate para el 10/10/04 (mismo día, así se permite crear la clase)
        mock_localdate.return_value = fecha_clase
        mock_now.return_value = dt(2004, 10, 10, 9, 0)
        mock_localtime.return_value = dt(2004, 10, 10, 9, 0)

        clase = self._crear_clase(
            fecha=fecha_clase,
            hora_inicio=time(10, 0),
            hora_fin=time(11, 0)
        )
        reserva = self._crear_reserva(clase, qr_usado=False)

        # Ahora cambiamos a la fecha 11/10/04 para que el QR esté vencido
        mock_localdate.return_value = date(2004, 10, 11)
        mock_now.return_value = dt(2004, 10, 11, 9, 50)
        mock_localtime.return_value = dt(2004, 10, 11, 9, 50)

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


# ─── Additional imports for ClaseFija tests ───────────────────────────────────

from decimal import Decimal as _Decimal
from django.contrib.messages import get_messages as _get_messages
from django.urls import reverse as _reverse

from turno.models import ClaseFija, Salon
from turno.services import generar_clases_fijas


# ─── Shared base ──────────────────────────────────────────────────────────────

class _ClaseFijaBase(TestCase):
    """Shared setUp for the three ClaseFija test suites."""

    def setUp(self):
        # Admin user — es_admin() accepts 'secretario' or 'dueno'
        self.admin = User.objects.create_user(
            username='admin_cf',
            email='admin_cf@test.com',
            password='test1234',
            dni='CF00001',
            telefono='1100001',
            rol='secretario',
        )

        # Active Actividad
        self.actividad = Actividad.objects.create(
            nombre='Act CF Test',
            descripcion='Actividad de prueba para clase fija',
            duracion_min=60,
            precio=_Decimal('5000'),
            activa=True,
        )

        # Two active Profesores (needed for conflict tests)
        self.profesor = Profesor.objects.create(
            nombre='Profe',
            apellido='TestCF',
            dni=99001,
            telefono='1100001',
            email='prof_cf@test.com',
            especialidad='Testing',
            activo=True,
        )
        self.profesor2 = Profesor.objects.create(
            nombre='Profe2',
            apellido='TestCF2',
            dni=99002,
            telefono='1100002',
            email='prof_cf2@test.com',
            especialidad='Testing2',
            activo=True,
        )

        # Two Salones
        self.salon = Salon.objects.create(nombre='Salon CF Test')
        self.salon2 = Salon.objects.create(nombre='Salon CF Test 2')

        # Base date for fixtures — always 7 days in the future (safely past today)
        self.hoy = timezone.localdate()
        self.fecha_inicio = self.hoy + timedelta(days=7)
        self.dia_semana = self.fecha_inicio.weekday()

        self.client.force_login(self.admin)


# ─── 1. View tests: crear_clase with es_recurrente ────────────────────────────

class CrearClaseFijaTests(_ClaseFijaBase):
    """POST to crear_clase with es_recurrente='on'."""

    def _post_data(self, **overrides):
        data = {
            'actividad': self.actividad.pk,
            'profesor': self.profesor.pk,
            'fecha': self.fecha_inicio.strftime('%Y-%m-%d'),
            'hora_inicio': '15:00',
            'cupo_maximo': 10,
            'salon': self.salon.pk,
            'es_recurrente': 'on',
        }
        data.update(overrides)
        return data

    def test_creacion_exitosa(self):
        """POST crea exactamente 1 ClaseFija y las Clase para el horizonte de 4 semanas."""
        url = _reverse('crear_clase')
        # Don't follow the redirect: messages are readable before template consumption.
        response = self.client.post(url, self._post_data())

        # Exactly one rule created
        self.assertEqual(ClaseFija.objects.count(), 1)
        regla = ClaseFija.objects.first()

        # Expected occurrence dates: fecha_inicio, +7, +14, +21 (all ≤ hoy+28)
        limite = self.hoy + timedelta(days=28)
        expected = []
        f = self.fecha_inicio
        while f <= limite:
            expected.append(f)
            f += timedelta(days=7)

        generated = sorted(
            Clase.objects.filter(clase_fija=regla).values_list('fecha', flat=True)
        )
        self.assertEqual(generated, expected, "Las fechas generadas no coinciden con las esperadas")

        # Success message must be present on the (unconsumed) redirect response
        msgs = [str(m) for m in _get_messages(response.wsgi_request)]
        self.assertTrue(
            any('Clase fija creada con éxito' in m for m in msgs),
            f"Mensajes encontrados: {msgs}",
        )

    def test_conflicto_salon_todo_o_nada(self):
        """Un conflicto de salón en cualquier fecha bloquea toda la creación de la regla."""
        # Pre-create a plain Clase on the 3rd occurrence (fecha_inicio+14), same salon,
        # different profesor so only the salon conflicts.
        fecha_conflicto = self.fecha_inicio + timedelta(days=14)
        Clase.objects.create(
            actividad=self.actividad,
            profesor=self.profesor2,   # different profesor
            salon=self.salon,           # same salon — triggers conflict
            fecha=fecha_conflicto,
            hora_inicio=time(15, 0),
            hora_fin=time(16, 0),
            cupo_maximo=10,
        )

        url = _reverse('crear_clase')
        response = self.client.post(url, self._post_data())

        # No ClaseFija should have been created
        self.assertEqual(ClaseFija.objects.count(), 0)
        # No clase_fija-linked Clase rows beyond the pre-created plain one
        self.assertEqual(Clase.objects.filter(clase_fija__isnull=False).count(), 0)

        # The view renders the form again (200) with error messages
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'no está disponible')
        self.assertContains(response, 'No se creó la clase fija')

    def test_conflicto_profesor_todo_o_nada(self):
        """Un conflicto de profesor en cualquier fecha bloquea toda la creación de la regla."""
        fecha_conflicto = self.fecha_inicio + timedelta(days=14)
        Clase.objects.create(
            actividad=self.actividad,
            profesor=self.profesor,    # same profesor — triggers conflict
            salon=self.salon2,          # different salon
            fecha=fecha_conflicto,
            hora_inicio=time(15, 0),
            hora_fin=time(16, 0),
            cupo_maximo=10,
        )

        url = _reverse('crear_clase')
        response = self.client.post(url, self._post_data())

        self.assertEqual(ClaseFija.objects.count(), 0)
        self.assertEqual(Clase.objects.filter(clase_fija__isnull=False).count(), 0)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'no está disponible')
        self.assertContains(response, 'No se creó la clase fija')

    def test_conflicto_con_otra_clase_fija(self):
        """Solapamiento con otra ClaseFija activa bloquea la nueva creación."""
        # Pre-create a conflicting active ClaseFija (same dia_semana + time window + salon)
        ClaseFija.objects.create(
            actividad=self.actividad,
            profesor=self.profesor2,
            salon=self.salon,
            dia_semana=self.dia_semana,
            hora_inicio=time(15, 0),
            hora_fin=time(16, 0),
            cupo_maximo=10,
            activa=True,
            fecha_inicio=self.fecha_inicio,
        )

        url = _reverse('crear_clase')
        response = self.client.post(url, self._post_data())

        # Count must still be 1 (only the pre-created rule)
        self.assertEqual(ClaseFija.objects.count(), 1)
        self.assertEqual(response.status_code, 200)


# ─── 2. Service tests: generar_clases_fijas() ─────────────────────────────────

class GenerarClasesFijasTests(_ClaseFijaBase):
    """Direct calls to the generar_clases_fijas() service."""

    def _crear_regla(self):
        return ClaseFija.objects.create(
            actividad=self.actividad,
            profesor=self.profesor,
            salon=self.salon,
            dia_semana=self.dia_semana,
            hora_inicio=time(15, 0),
            hora_fin=time(16, 0),
            cupo_maximo=10,
            activa=True,
            fecha_inicio=self.fecha_inicio,
        )

    def test_idempotente(self):
        """Llamar dos veces a generar_clases_fijas() no duplica las Clase generadas."""
        regla = self._crear_regla()

        generar_clases_fijas()
        count_first = Clase.objects.filter(clase_fija=regla).count()

        generar_clases_fijas()
        count_second = Clase.objects.filter(clase_fija=regla).count()

        self.assertEqual(count_first, count_second, "Segunda llamada duplicó filas")
        self.assertGreater(count_first, 0, "No se generó ninguna Clase")

        limite = self.hoy + timedelta(days=28)
        for c in Clase.objects.filter(clase_fija=regla):
            self.assertLessEqual(
                c.fecha, limite,
                f"Clase generada en {c.fecha} supera el horizonte {limite}",
            )

    def test_conflicto_saltea_ocurrencia(self):
        """Una ocurrencia en conflicto se saltea; el resto se genera normalmente."""
        # 2nd occurrence = fecha_inicio + 7 days
        fecha_2da = self.fecha_inicio + timedelta(days=7)

        # Blocking plain Clase: same salon + same hora_inicio → Clase.clean() raises
        # ValidationError when the service tries to create the 2nd occurrence.
        Clase.objects.create(
            actividad=self.actividad,
            profesor=self.profesor2,   # different profesor so the 1st/3rd/4th won't block
            salon=self.salon,
            fecha=fecha_2da,
            hora_inicio=time(15, 0),
            hora_fin=time(16, 0),
            cupo_maximo=10,
        )

        regla = self._crear_regla()
        # Must not raise even though 1 date conflicts
        generar_clases_fijas()

        # The 2nd occurrence should NOT have a clase_fija-linked Clase
        self.assertFalse(
            Clase.objects.filter(clase_fija=regla, fecha=fecha_2da).exists(),
            f"La fecha {fecha_2da} debería haber sido salteada por conflicto de salón",
        )

        # The other 3 occurrences (dates 0, +14, +21 from fecha_inicio) SHOULD exist
        limite = self.hoy + timedelta(days=28)
        for days_offset in (0, 14, 21):
            f = self.fecha_inicio + timedelta(days=days_offset)
            if f <= limite:
                self.assertTrue(
                    Clase.objects.filter(clase_fija=regla, fecha=f).exists(),
                    f"La fecha {f} debería haber sido generada pero no existe",
                )


# ─── 3. View tests: terminar_clase_fija ───────────────────────────────────────

class TerminarClaseFijaTests(_ClaseFijaBase):
    """POST to terminar_clase_fija terminates the rule and cancels future occurrences."""

    def setUp(self):
        super().setUp()

        # Regular client user for reservas
        self.cliente = User.objects.create_user(
            username='cliente_cf',
            email='cliente_cf@test.com',
            password='test1234',
            dni='CF00002',
            telefono='1100099',
            rol='cliente',
        )

        # Create rule and generate the first wave of classes
        self.regla = ClaseFija.objects.create(
            actividad=self.actividad,
            profesor=self.profesor,
            salon=self.salon,
            dia_semana=self.dia_semana,
            hora_inicio=time(15, 0),
            hora_fin=time(16, 0),
            cupo_maximo=10,
            activa=True,
            fecha_inicio=self.fecha_inicio,
        )
        generar_clases_fijas()

    def test_terminar_clase_fija(self):
        """POST desactiva la regla, cancela clases futuras con motivo y cancela sus reservas."""
        # Pick a future generated class for the reserva
        clase_futura = (
            Clase.objects.filter(clase_fija=self.regla, cancelada=False)
            .order_by('fecha')
            .first()
        )
        self.assertIsNotNone(clase_futura, "Debe haber al menos una Clase generada")

        # Create a Reserva on that class
        reserva = Reserva.objects.create(
            usuario=self.cliente,
            clase=clase_futura,
            estado='confirmada',
        )

        url = _reverse('terminar_clase_fija', args=[self.regla.id])
        self.client.post(url)

        # The rule must be inactive
        self.regla.refresh_from_db()
        self.assertFalse(self.regla.activa, "La regla debe quedar con activa=False")

        # All generated instances must be cancelled with the correct motivo
        clases_generadas = Clase.objects.filter(clase_fija=self.regla)
        self.assertGreater(clases_generadas.count(), 0)
        for clase in clases_generadas:
            clase.refresh_from_db()
            self.assertTrue(
                clase.cancelada,
                f"Clase del {clase.fecha} debería estar cancelada",
            )
            self.assertEqual(
                clase.motivo_cancelacion,
                "Clase fija terminada por administración",
                f"Motivo incorrecto en clase del {clase.fecha}: {clase.motivo_cancelacion!r}",
            )

        # The reserva must be cancelled
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, 'cancelada', "La reserva debe quedar en estado 'cancelada'")

        # generar_clases_fijas() must NOT create new Clase rows (rule is inactive)
        count_before = Clase.objects.filter(clase_fija=self.regla).count()
        generar_clases_fijas()
        count_after = Clase.objects.filter(clase_fija=self.regla).count()
        self.assertEqual(
            count_before, count_after,
            "generar_clases_fijas() creó nuevas clases para una regla terminada",
        )
