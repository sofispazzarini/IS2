from django.db import models

from user.models import User
from actividad.models import Actividad
from turno.models import Clase


class Resena(models.Model):

    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    actividad = models.ForeignKey(
        Actividad,
        on_delete=models.CASCADE
    )

    clase = models.ForeignKey(
        Clase,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='resenas'
    )

    puntuacion = models.IntegerField()

    comentario = models.TextField()

    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['usuario', 'actividad'], name='unique_usuario_actividad')
        ]

    def __str__(self):
        if self.clase:
            return f"{self.usuario.username} - {self.clase}"
        return f"{self.usuario.username} - {self.actividad.nombre}"