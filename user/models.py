from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    ROLES = (
        ('cliente', 'Cliente'),
        ('secretario', 'Secretario'),
        ('dueno', 'Dueño'),
    )

    dni = models.CharField(max_length=20, unique=True)
    telefono = models.CharField(max_length=20)
    fecha_nacimiento = models.DateField(null=True, blank=True)

    rol = models.CharField(
        max_length=20,
        choices=ROLES,
        default='cliente'
    )

    activo = models.BooleanField(default=True)

    notificaciones_activas = models.BooleanField(default=True)

    creditos = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.username} ({self.rol})"


class Profesor(models.Model):

    nombre = models.CharField(max_length=100)

    apellido = models.CharField(max_length=100)

    telefono = models.CharField(max_length=20)

    email = models.EmailField()

    especialidad = models.CharField(max_length=100)

    descripcion = models.TextField(blank=True)

    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"


class Penalizacion(models.Model):

    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='penalizaciones'
    )

    motivo = models.TextField()

    fecha = models.DateTimeField(auto_now_add=True)

    activa = models.BooleanField(default=True)

    def __str__(self):
        return f"Penalización - {self.usuario.username}"


class HistorialUsuarioBaja(models.Model):

    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    email = models.EmailField()
    dni = models.CharField(max_length=20)
    telefono = models.CharField(max_length=20)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    fecha_registro_original = models.DateTimeField()
    creditos_al_momento = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    fecha_baja = models.DateTimeField(auto_now_add=True)
    dado_baja_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='bajas_realizadas'
    )
    motivo = models.TextField(blank=True)

    def __str__(self):
        return f"Baja: {self.email} - {self.fecha_baja.strftime('%d/%m/%Y')}"