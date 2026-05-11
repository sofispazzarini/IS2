from django.db import models

from user.models import User
from actividad.models import Actividad


class Resena(models.Model):

    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    actividad = models.ForeignKey(
        Actividad,
        on_delete=models.CASCADE
    )

    puntuacion = models.IntegerField()

    comentario = models.TextField()

    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario.username} - {self.actividad.nombre}"