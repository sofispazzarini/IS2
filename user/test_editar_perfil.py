from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from .forms import EditarPerfilForm
from datetime import date

User = get_user_model()


class EditarPerfilFormTestCase(TestCase):
    """Tests para el formulario de edición de perfil."""

    def setUp(self):
        """Crear usuario de prueba."""
        self.user = User.objects.create_user(
            username="juanignacio@gmail.com",
            email="juanignacio@gmail.com",
            first_name="Juan Ignacio",
            last_name="Torre",
            dni="47032818",
            telefono="4802893",
            password="Password123",
            fecha_nacimiento=date(2006, 5, 2),
        )
        self.client = Client()

    def test_escenario_1_modificacion_exitosa(self):
        """
        Escenario I: Modificación exitosa
        Dado un usuario con nombre y apellido "Juan Ignacio Torre" y telefono "4802893"
        Cuando reemplaza su nombre por "Juan", apellido por "Torres", 
        telefono por "4802894" y presiona "Guardar cambios",
        Entonces el sistema actualiza los cambios en la base de datos 
        y muestra el mensaje "Datos actualizados exitosamente".
        """
        data = {
            "first_name": "Juan",
            "last_name": "Torres",
            "telefono": "4802894",
        }
        form = EditarPerfilForm(data, instance=self.user, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        
        form.save()
        self.user.refresh_from_db()
        
        self.assertEqual(self.user.first_name, "Juan")
        self.assertEqual(self.user.last_name, "Torres")
        self.assertEqual(self.user.telefono, "4802894")

    def test_nombre_solo_letras(self):
        """
        El campo nombre debe rechazar números y caracteres especiales.
        """
        data = {
            "first_name": "Juan123",
            "last_name": "Torres",
            "telefono": "4802894",
        }
        form = EditarPerfilForm(data, instance=self.user, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("first_name", form.errors)
        self.assertIn("solo puede contener letras", str(form.errors["first_name"]))

    def test_apellido_solo_letras(self):
        """
        El campo apellido debe rechazar números y caracteres especiales.
        """
        data = {
            "first_name": "Juan",
            "last_name": "Torres123",
            "telefono": "4802894",
        }
        form = EditarPerfilForm(data, instance=self.user, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("last_name", form.errors)
        self.assertIn("solo puede contener letras", str(form.errors["last_name"]))

    def test_telefono_solo_numeros(self):
        """
        El campo teléfono debe rechazar letras y caracteres especiales.
        """
        data = {
            "first_name": "Juan",
            "last_name": "Torres",
            "telefono": "480-ABC-94",
        }
        form = EditarPerfilForm(data, instance=self.user, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("telefono", form.errors)
        self.assertIn("solo puede contener números", str(form.errors["telefono"]))

    def test_nombre_obligatorio(self):
        """El campo nombre es obligatorio."""
        data = {
            "first_name": "",
            "last_name": "Torres",
            "telefono": "4802894",
        }
        form = EditarPerfilForm(data, instance=self.user, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("first_name", form.errors)
        self.assertIn("obligatorio", str(form.errors["first_name"]))

    def test_apellido_obligatorio(self):
        """El campo apellido es obligatorio."""
        data = {
            "first_name": "Juan",
            "last_name": "",
            "telefono": "4802894",
        }
        form = EditarPerfilForm(data, instance=self.user, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("last_name", form.errors)
        self.assertIn("obligatorio", str(form.errors["last_name"]))

    def test_nombre_con_acentos(self):
        """El nombre debe permitir acentos."""
        data = {
            "first_name": "José",
            "last_name": "López",
            "telefono": "4802894",
        }
        form = EditarPerfilForm(data, instance=self.user, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_nombre_con_espacios(self):
        """El nombre debe permitir espacios."""
        data = {
            "first_name": "Juan Ignacio",
            "last_name": "de la Torre",
            "telefono": "4802894",
        }
        form = EditarPerfilForm(data, instance=self.user, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)


class EditarPerfilViewTestCase(TestCase):
    """Tests para la vista de edición de perfil."""

    def setUp(self):
        """Crear usuario de prueba."""
        self.user = User.objects.create_user(
            username="juanignacio@gmail.com",
            email="juanignacio@gmail.com",
            first_name="Juan Ignacio",
            last_name="Torre",
            dni="47032818",
            telefono="4802893",
            password="Password123",
            fecha_nacimiento=date(2006, 5, 2),
        )
        self.client = Client()

    def test_perfil_requiere_autenticacion(self):
        """La vista de perfil debe requerir autenticación."""
        response = self.client.get(reverse('user:perfil'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('user:login'), response['Location'])

    def test_perfil_vista_se_carga(self):
        """La vista de perfil debe cargarse correctamente."""
        self.client.login(username="juanignacio@gmail.com", password="Password123")
        response = self.client.get(reverse('user:perfil'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mi Perfil")

    def test_actualizar_perfil_exitoso(self):
        """
        Actualizar datos del perfil debe mostrar el mensaje de éxito.
        """
        self.client.login(username="juanignacio@gmail.com", password="Password123")
        
        data = {
            "first_name": "Juan",
            "last_name": "Torres",
            "telefono": "4802894",
            "guardar_perfil": "on",
        }
        
        response = self.client.post(reverse('user:perfil'), data, follow=True)
        
        # Verificar que se actualizo en la BD
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Juan")
        self.assertEqual(self.user.last_name, "Torres")
        self.assertEqual(self.user.telefono, "4802894")
        
        # Verificar el mensaje de éxito
        messages_list = list(response.context['messages'])
        self.assertTrue(any('Datos actualizados exitosamente' in str(m) for m in messages_list))

    def test_actualizar_solo_telefono(self):
        """
        Actualizar solo el teléfono debe mostrar mensaje específico.
        """
        self.client.login(username="juanignacio@gmail.com", password="Password123")
        
        data = {
            "first_name": "Juan Ignacio",
            "last_name": "Torre",
            "telefono": "4802894",
            "guardar_perfil": "on",
        }
        
        response = self.client.post(reverse('user:perfil'), data, follow=True)
        
        # Verificar que se actualizó en la BD
        self.user.refresh_from_db()
        self.assertEqual(self.user.telefono, "4802894")
        
        # Verificar el mensaje
        messages_list = list(response.context['messages'])
        self.assertTrue(any('Teléfono actualizado exitosamente' in str(m) for m in messages_list))
