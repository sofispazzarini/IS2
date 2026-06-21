from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from .forms import CrearSecretarioForm
from datetime import date

User = get_user_model()


class CrearSecretarioFormTestCase(TestCase):
    """Tests para el formulario de crear secretario."""

    def test_escenario_1_alta_exitosa(self):
        """
        Escenario I: Alta exitosa
        Dado un secretario Joaquin Facu con mail joacofacu@gmail.com y DNI 2727723 
        no registrados en el sistema.
        Cuando ingresa los datos personales del nuevo secretario nombre:Joaquin, 
        apellido: Facu, DNI: 2837, mail: joacofacu@gmail.com y presiona "Crear Cuenta".
        Entonces el sistema crea una cuenta para el usuario, le otorga los permisos 
        de secretario e informa "Cuenta creada exitosamente".
        """
        data = {
            "first_name": "Joaquin",
            "last_name": "Facu",
            "email": "joacofacu@gmail.com",
            "dni": "2837",
            "telefono": "1234567890",
            "password": "Password123",
            "password_confirm": "Password123",
        }
        form = CrearSecretarioForm(data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_escenario_2_alta_fallida_email_duplicado(self):
        """
        Escenario II: Alta fallida - Email duplicado
        """
        # Crear usuario existente
        User.objects.create_user(
            username="joacofacu@gmail.com",
            email="joacofacu@gmail.com",
            first_name="Juan",
            last_name="Pérez",
            dni="1234567",
            telefono="1234567890",
            password="Password123",
        )

        # Intentar crear secretario con email duplicado
        data = {
            "first_name": "Joaquin",
            "last_name": "Facu",
            "email": "joacofacu@gmail.com",
            "dni": "2837",
            "telefono": "1234567890",
            "password": "Password123",
            "password_confirm": "Password123",
        }
        form = CrearSecretarioForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_escenario_2_alta_fallida_dni_duplicado(self):
        """
        Escenario II: Alta fallida - DNI duplicado
        """
        # Crear usuario existente
        User.objects.create_user(
            username="otro@gmail.com",
            email="otro@gmail.com",
            first_name="Juan",
            last_name="Pérez",
            dni="2837",
            telefono="1234567890",
            password="Password123",
        )

        # Intentar crear secretario con DNI duplicado
        data = {
            "first_name": "Joaquin",
            "last_name": "Facu",
            "email": "joacofacu@gmail.com",
            "dni": "2837",
            "telefono": "1234567890",
            "password": "Password123",
            "password_confirm": "Password123",
        }
        form = CrearSecretarioForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("dni", form.errors)

    def test_contraseñas_no_coinciden(self):
        """Las contraseñas deben coincidir."""
        data = {
            "first_name": "Joaquin",
            "last_name": "Facu",
            "email": "joacofacu@gmail.com",
            "dni": "2837",
            "telefono": "1234567890",
            "password": "Password123",
            "password_confirm": "Password456",
        }
        form = CrearSecretarioForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("No coinciden", str(form.errors))

    def test_contraseña_muy_corta(self):
        """La contraseña debe tener mínimo 8 caracteres."""
        data = {
            "first_name": "Joaquin",
            "last_name": "Facu",
            "email": "joacofacu@gmail.com",
            "dni": "2837",
            "telefono": "1234567890",
            "password": "Pass123",
            "password_confirm": "Pass123",
        }
        form = CrearSecretarioForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("password", form.errors)


class CrearSecretarioViewTestCase(TestCase):
    """Tests para la vista de crear secretario."""

    def setUp(self):
        """Crear usuario dueño para pruebas."""
        self.dueno = User.objects.create_user(
            username="dueno@sirca.com",
            email="dueno@sirca.com",
            first_name="Dueño",
            last_name="Sistema",
            dni="12345678",
            telefono="1234567890",
            password="Password123",
            rol="dueno",
        )
        self.client = Client()

    def test_crear_secretario_requiere_autenticacion(self):
        """La vista de crear secretario debe requerir autenticación."""
        response = self.client.get(reverse('user:crear_secretario'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('user:login'), response['Location'])

    def test_crear_secretario_requiere_ser_dueno(self):
        """Solo el dueño puede crear secretarios."""
        cliente = User.objects.create_user(
            username="cliente@sirca.com",
            email="cliente@sirca.com",
            first_name="Cliente",
            last_name="Test",
            dni="87654321",
            telefono="1234567890",
            password="Password123",
            rol="cliente",
        )
        self.client.login(username="cliente@sirca.com", password="Password123")
        response = self.client.get(reverse('user:crear_secretario'))
        self.assertEqual(response.status_code, 403)

    def test_crear_secretario_exitoso(self):
        """Crear un secretario exitosamente desde la vista."""
        self.client.login(username="dueno@sirca.com", password="Password123")

        data = {
            "first_name": "Joaquin",
            "last_name": "Facu",
            "email": "joacofacu@gmail.com",
            "dni": "2837",
            "telefono": "1234567890",
            "password": "Password123",
            "password_confirm": "Password123",
        }

        response = self.client.post(reverse('user:crear_secretario'), data, follow=True)

        # Verificar que se creó el usuario
        secretario = User.objects.get(email="joacofacu@gmail.com")
        self.assertEqual(secretario.first_name, "Joaquin")
        self.assertEqual(secretario.last_name, "Facu")
        self.assertEqual(secretario.rol, "secretario")
        self.assertEqual(secretario.dni, "2837")

        # Verificar que se redirigió
        self.assertEqual(response.status_code, 200)

        # Verificar el mensaje de éxito
        messages_list = list(response.context['messages'])
        self.assertTrue(any('Cuenta creada exitosamente' in str(m) for m in messages_list))

    def test_admin_secretarios_requiere_ser_dueno(self):
        """Solo el dueño puede acceder al panel de secretarios."""
        cliente = User.objects.create_user(
            username="cliente@sirca.com",
            email="cliente@sirca.com",
            first_name="Cliente",
            last_name="Test",
            dni="87654321",
            telefono="1234567890",
            password="Password123",
            rol="cliente",
        )
        self.client.login(username="cliente@sirca.com", password="Password123")
        response = self.client.get(reverse('user:admin_secretarios'))
        self.assertEqual(response.status_code, 403)

    def test_admin_secretarios_dueño(self):
        """El dueño puede acceder al panel de secretarios."""
        self.client.login(username="dueno@sirca.com", password="Password123")
        response = self.client.get(reverse('user:admin_secretarios'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Secretarios del sistema")

    def test_listar_secretarios(self):
        """Verificar que el listado de secretarios funciona."""
        # Crear algunos secretarios
        User.objects.create_user(
            username="secretario1@sirca.com",
            email="secretario1@sirca.com",
            first_name="Secretario",
            last_name="Uno",
            dni="1111111",
            telefono="1234567890",
            password="Password123",
            rol="secretario",
        )
        User.objects.create_user(
            username="secretario2@sirca.com",
            email="secretario2@sirca.com",
            first_name="Secretario",
            last_name="Dos",
            dni="2222222",
            telefono="1234567890",
            password="Password123",
            rol="secretario",
        )

        self.client.login(username="dueno@sirca.com", password="Password123")
        response = self.client.get(reverse('user:admin_secretarios'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Secretario Uno")
        self.assertContains(response, "Secretario Dos")
