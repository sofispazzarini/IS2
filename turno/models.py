import uuid

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

from user.models import User, Profesor
from actividad.models import Actividad


class Clase(models.Model):

    actividad = models.ForeignKey(
        Actividad,
        on_delete=models.PROTECT,
        related_name='clases'
    )

    profesor = models.ForeignKey(
        Profesor,
        on_delete=models.PROTECT,
        related_name='clases'
    )

    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    cupo_maximo = models.IntegerField()
    salon = models.CharField(max_length=100)
    cancelada = models.BooleanField(default=False)
    motivo_cancelacion = models.TextField(
        blank=True,
        null=True
    )

    def clean(self):
        if self.fecha and self.fecha < timezone.localdate():
            raise ValidationError("no puedes crear una actividad para una fecha pasada")

        salon_ocupado = Clase.objects.filter(
            fecha=self.fecha,
            hora_inicio=self.hora_inicio,
            salon=self.salon
        ).exclude(pk=self.pk)

        if salon_ocupado.exists():
            raise ValidationError(f"salon no disponible para el {self.fecha} a las {self.hora_inicio}")

        profesor_ocupado = Clase.objects.filter(
            fecha=self.fecha,
            hora_inicio=self.hora_inicio,
            profesor=self.profesor
        ).exclude(pk=self.pk)

        if profesor_ocupado.exists():
            raise ValidationError(f"profesor no disponible para el {self.fecha} a las {self.hora_inicio}")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.actividad.nombre} - {self.fecha}"


class Reserva(models.Model):

    ESTADOS = (
        ('pendiente_pago', 'Pendiente de pago'),
        ('confirmada', 'Confirmada'),
        ('cancelada', 'Cancelada'),
        ('asistida', 'Asistida'),
        ('ausente', 'Ausente'),
    )

    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reservas'
    )

    clase = models.ForeignKey(
        Clase,
        on_delete=models.CASCADE,
        related_name='reservas'
    )

    fecha_reserva = models.DateTimeField(auto_now_add=True)

    estado = models.CharField(
        max_length=30,
        choices=ESTADOS,
        default='pendiente_pago'
    )

    qr_uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )

    observaciones = models.TextField(
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.usuario.username} - {self.clase}"


class Asistencia(models.Model):

    reserva = models.OneToOneField(
        Reserva,
        on_delete=models.CASCADE,
        related_name='asistencia'
    )

    fecha_registro = models.DateTimeField(auto_now_add=True)

    presente = models.BooleanField(default=True)

    registrado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )

    def __str__(self):
        return f"Asistencia - {self.reserva}"


class ListaEspera(models.Model):

    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    clase = models.ForeignKey(
        Clase,
        on_delete=models.CASCADE
    )

    fecha_ingreso = models.DateTimeField(auto_now_add=True)

    notificado = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.usuario.username} - {self.clase}"