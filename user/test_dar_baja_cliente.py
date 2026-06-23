from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from user.models import HistorialUsuarioBaja

User = get_user_model()


class DarBajaClienteTestCase(TestCase):
    """Tests para la funcionalidad de dar de baja a un cliente."""

    def setUp(self):
        """Crear usuarios para pruebas."""
        # Usuario dueño
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

        # Usuario secretario
        self.secretario = User.objects.create_user(
            username="secretario@sirca.com",
            email="secretario@sirca.com",
            first_name="Secretario",
            last_name="Test",
            dni="87654321",
            telefono="9876543210",
            password="Password123",
            rol="secretario",
        )

        # Usuario cliente a dar de baja
        self.cliente = User.objects.create_user(
            username="usuariotestinge2@gmail.com",
            email="usuariotestinge2@gmail.com",
            first_name="Juani",
            last_name="Torres",
            dni="19876543",
            telefono="1122334455",
            password="Password123",
            rol="cliente",
            creditos=150.00,
        )

        self.client = Client()

    def test_escenario_1_baja_exitosa(self):
        """
        Escenario I: Baja lógica exitosa
        Dado un perfil de cliente "Juani Torres", registrado en el sistema 
        con el mail "usuariotestinge2@gmail.com"
        Cuando se presiona "Eliminar usuario" y confirma la operacion
        Entonces el sistema guarda los datos del usuario, elimina su cuenta 
        e informa "Usuario eliminado exitosamente. Los datos fueron guardados en el historial."
        """
        # Verificar que el cliente existe
        self.assertTrue(User.objects.filter(email="usuariotestinge2@gmail.com").exists())

        # Ingresar como secretario
        self.client.login(username="secretario@sirca.com", password="Password123")

        # POST a dar de baja cliente
        response = self.client.post(
            reverse('user:dar_baja_cliente', args=[self.cliente.pk]),
            follow=True
        )

        # Verificar que se redirigió a client_list
        self.assertEqual(response.status_code, 200)

        # Verificar el mensaje de éxito
        messages_list = list(response.context['messages'])
        self.assertTrue(
            any(
                'Usuario eliminado exitosamente. Los datos fueron guardados en el historial.' 
                in str(m) 
                for m in messages_list
            ),
            f"Mensaje esperado no encontrado. Mensajes: {[str(m) for m in messages_list]}"
        )

        # Verificar que el usuario fue eliminado
        self.assertFalse(User.objects.filter(pk=self.cliente.pk).exists())

        # Verificar que el historial fue guardado
        historial = HistorialUsuarioBaja.objects.filter(
            email="usuariotestinge2@gmail.com"
        )
        self.assertTrue(historial.exists())

        # Verificar los datos guardados en el historial
        registro_historial = historial.first()
        self.assertEqual(registro_historial.nombre, "Juani")
        self.assertEqual(registro_historial.apellido, "Torres")
        self.assertEqual(registro_historial.email, "usuariotestinge2@gmail.com")
        self.assertEqual(registro_historial.dni, "19876543")
        self.assertEqual(registro_historial.telefono, "1122334455")
        self.assertEqual(registro_historial.creditos_al_momento, 150.00)
        self.assertEqual(registro_historial.dado_baja_por, self.secretario)

    def test_dar_baja_requiere_autenticacion(self):
        """La vista de dar de baja debe requerir autenticación."""
        response = self.client.get(
            reverse('user:dar_baja_cliente', args=[self.cliente.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('user:login'), response['Location'])

    def test_dar_baja_requiere_ser_admin(self):
        """Solo secretarios y dueños pueden dar de baja a clientes."""
        # Crear un cliente intenta dar de baja a otro cliente
        cliente2 = User.objects.create_user(
            username="cliente2@sirca.com",
            email="cliente2@sirca.com",
            first_name="Cliente",
            last_name="Dos",
            dni="11111111",
            telefono="1234567890",
            password="Password123",
            rol="cliente",
        )

        self.client.login(username="cliente2@sirca.com", password="Password123")
        response = self.client.get(
            reverse('user:dar_baja_cliente', args=[self.cliente.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_dar_baja_por_dueno(self):
        """El dueño puede dar de baja a un cliente."""
        self.client.login(username="dueno@sirca.com", password="Password123")

        response = self.client.post(
            reverse('user:dar_baja_cliente', args=[self.cliente.pk]),
            follow=True
        )

        self.assertEqual(response.status_code, 200)
        
        # Verificar que el usuario fue eliminado
        self.assertFalse(User.objects.filter(pk=self.cliente.pk).exists())

        # Verificar que el historial fue guardado por el dueño
        historial = HistorialUsuarioBaja.objects.get(email="usuariotestinge2@gmail.com")
        self.assertEqual(historial.dado_baja_por, self.dueno)

    def test_historial_guarda_todos_los_datos(self):
        """Verificar que el historial guarda todos los datos del cliente."""
        self.client.login(username="secretario@sirca.com", password="Password123")

        # Verificar datos antes de la baja
        self.assertEqual(self.cliente.first_name, "Juani")
        self.assertEqual(self.cliente.last_name, "Torres")
        self.assertEqual(self.cliente.telefono, "1122334455")
        self.assertEqual(self.cliente.creditos, 150.00)

        # Dar de baja
        self.client.post(
            reverse('user:dar_baja_cliente', args=[self.cliente.pk])
        )

        # Verificar historial
        historial = HistorialUsuarioBaja.objects.get(email="usuariotestinge2@gmail.com")
        self.assertEqual(historial.nombre, "Juani")
        self.assertEqual(historial.apellido, "Torres")
        self.assertEqual(historial.email, "usuariotestinge2@gmail.com")
        self.assertEqual(historial.dni, "19876543")
        self.assertEqual(historial.telefono, "1122334455")
        self.assertEqual(historial.creditos_al_momento, 150.00)
        self.assertEqual(historial.fecha_registro_original, self.cliente.fecha_registro)

    def test_get_muestra_formulario_confirmacion(self):
        """GET debe mostrar la página de confirmación."""
        self.client.login(username="secretario@sirca.com", password="Password123")

        response = self.client.get(
            reverse('user:dar_baja_cliente', args=[self.cliente.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Confirmar baja de cliente")
        self.assertContains(response, "Juani Torres")
        self.assertContains(response, "usuariotestinge2@gmail.com")

    def test_no_se_puede_dar_baja_cliente_inexistente(self):
        """No se puede dar de baja a un cliente que no existe."""
        self.client.login(username="secretario@sirca.com", password="Password123")

        response = self.client.get(
            reverse('user:dar_baja_cliente', args=[9999])
        )

        self.assertEqual(response.status_code, 404)
