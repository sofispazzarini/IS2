from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from .forms import RegistroForm
from django.test import Client
from django.urls import reverse

User = get_user_model()


class RegistroFormTestCase(TestCase):
    """Tests para el formulario de registro"""

    def test_registro_exitoso(self):
        """Escenario I: Registro exitoso"""
        fecha_nac = date(2006, 5, 2)
        data = {
            "first_name": "Juan Ignacio",
            "last_name": "Torres",
            "email": "juanitorres@gmail.com",
            "dni": "47032818",
            "telefono": "221 3456 7890",
            "fecha_nacimiento": fecha_nac,
            "password": "juani123torres",
            "password_confirm": "juani123torres",
        }
        form = RegistroForm(data)
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertIsNotNone(user.pk)
        self.assertEqual(user.email, "juanitorres@gmail.com")
        self.assertEqual(user.dni, "47032818")

    def test_registro_falla_por_edad(self):
        """Escenario II: Registro fallido por falta de edad"""
        hoy = date.today()
        fecha_nac = date(hoy.year - 14, 5, 2)  # 14 años

        data = {
            "first_name": "Juan Ignacio",
            "last_name": "Torres",
            "email": "juanitorres@gmail.com",
            "dni": "47032818",
            "telefono": "221 3456 7890",
            "fecha_nacimiento": fecha_nac,
            "password": "juani123torres",
            "password_confirm": "juani123torres",
        }
        form = RegistroForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("fecha_nacimiento", form.errors)
        self.assertIn("Tenes que tener al menos 15 años", str(form.errors["fecha_nacimiento"]))

    def test_registro_falla_por_email_duplicado(self):
        """Escenario III: Registro fallido por correo electrónico duplicado"""
        fecha_nac = date(2006, 5, 2)

        User.objects.create_user(
            username="existing@gmail.com",
            email="juanitorres@gmail.com",
            dni="12345678",
            password="password123",
            fecha_nacimiento=fecha_nac,
        )

        data = {
            "first_name": "Juan Ignacio",
            "last_name": "Torres",
            "email": "juanitorres@gmail.com",
            "dni": "47032818",
            "telefono": "221 3456 7890",
            "fecha_nacimiento": fecha_nac,
            "password": "juani123torres",
            "password_confirm": "juani123torres",
        }
        form = RegistroForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
        self.assertIn("Este correo ya está asociado a una cuenta", str(form.errors["email"]))

    def test_registro_falla_por_dni_duplicado(self):
        """Escenario IV: Registro fallido por DNI duplicado"""
        fecha_nac = date(2006, 5, 2)

        User.objects.create_user(
            username="existing@gmail.com",
            email="existing@gmail.com",
            dni="47032818",
            password="password123",
            fecha_nacimiento=fecha_nac,
        )

        data = {
            "first_name": "Juan Ignacio",
            "last_name": "Torres",
            "email": "juanitorres@gmail.com",
            "dni": "47032818",
            "telefono": "221 3456 7890",
            "fecha_nacimiento": fecha_nac,
            "password": "juani123torres",
            "password_confirm": "juani123torres",
        }
        form = RegistroForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("dni", form.errors)
        self.assertIn("DNI ya asociado a una cuenta", str(form.errors["dni"]))

    def test_registro_falla_por_contrasena_corta(self):
        """Escenario V: Registro fallido por contraseña fuera de rango"""
        fecha_nac = date(2006, 5, 2)

        data = {
            "first_name": "Juan Ignacio",
            "last_name": "Torres",
            "email": "juanitorres@gmail.com",
            "dni": "47032818",
            "telefono": "221 3456 7890",
            "fecha_nacimiento": fecha_nac,
            "password": "Juani",
            "password_confirm": "Juani",
        }
        form = RegistroForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("password", form.errors)
        self.assertIn("Tu contraseña debe tener entre 8 y 20 caracteres", str(form.errors["password"]))

    def test_registro_falla_por_contrasena_larga(self):
        """Registro fallido por contraseña mayor a 20 caracteres"""
        fecha_nac = date(2006, 5, 2)

        data = {
            "first_name": "Juan Ignacio",
            "last_name": "Torres",
            "email": "juanitorres@gmail.com",
            "dni": "47032818",
            "telefono": "221 3456 7890",
            "fecha_nacimiento": fecha_nac,
            "password": "juani123torres1234901",
            "password_confirm": "juani123torres1234901",
        }
        form = RegistroForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("password", form.errors)
        self.assertIn("Tu contraseña debe tener entre 8 y 20 caracteres", str(form.errors["password"]))

    def test_contrasenas_no_coinciden(self):
        """Validar que las contraseñas coincidan"""
        fecha_nac = date(2006, 5, 2)

        data = {
            "first_name": "Juan Ignacio",
            "last_name": "Torres",
            "email": "juanitorres@gmail.com",
            "dni": "47032818",
            "telefono": "221 3456 7890",
            "fecha_nacimiento": fecha_nac,
            "password": "juani123torres",
            "password_confirm": "diferente123",
        }
        form = RegistroForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("Las contraseñas no coinciden", str(form.errors))


class LoginViewTestCase(TestCase):
    """Tests para la vista de login"""

    def setUp(self):
        self.client = Client()
        fecha_nac = date(2006, 5, 2)
        self.user = User.objects.create_user(
            username="juanitorreslp@gmail.com",
            email="juanitorreslp@gmail.com",
            password="Estudiantes7",
            first_name="Juan",
            last_name="Torres",
            dni="47032818",
            fecha_nacimiento=fecha_nac,
        )

    def test_login_exitoso(self):
        """Escenario I: Inicio de Sesión Exitoso"""
        response = self.client.post(reverse('user:login'), {
            'email': 'juanitorreslp@gmail.com',
            'password': 'Estudiantes7'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/')
        # Verificar que el usuario esté logueado
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_login_falla_usuario_no_registrado(self):
        """Escenario II: Inicio fallido por usuario no registrado"""
        response = self.client.post(reverse('user:login'), {
            'email': 'juanitorreslp@gmail.com',  # mismo email pero usuario no existe? Wait, el usuario existe, pero para testear no registrado, usar otro email
            'password': 'Estudiantes7'
        })
        # Este pasa porque el usuario existe. Para testear no registrado, usar email diferente.
        response = self.client.post(reverse('user:login'), {
            'email': 'noexiste@gmail.com',
            'password': 'Estudiantes7'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "El correo ingresado no se encuentra registrado")

    def test_login_falla_contrasena_invalida(self):
        """Escenario III: Inicio fallido por contraseña"""
        response = self.client.post(reverse('user:login'), {
            'email': 'juanitorreslp@gmail.com',
            'password': 'Estudiantes'  # contraseña incorrecta
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "La contraseña ingresada es inválida")
