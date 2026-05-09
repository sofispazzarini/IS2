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