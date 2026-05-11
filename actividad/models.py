from django.db import models
from user.models import Profesor


class Actividad(models.Model):

    nombre = models.CharField(max_length=100)

    descripcion = models.TextField()

    duracion_min = models.IntegerField()

    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    activa = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class DisponibilidadProfesor(models.Model):

    DIAS = (
        (0, 'Lunes'),
        (1, 'Martes'),
        (2, 'Miércoles'),
        (3, 'Jueves'),
        (4, 'Viernes'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    )

    profesor = models.ForeignKey(
        Profesor,
        on_delete=models.CASCADE,
        related_name='disponibilidades'
    )

    dia_semana = models.IntegerField(choices=DIAS)

    hora_inicio = models.TimeField()

    hora_fin = models.TimeField()

    def __str__(self):
        return f"{self.profesor} - {self.get_dia_semana_display()}"