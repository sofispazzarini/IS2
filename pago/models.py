from django.db import models

from turno.models import Reserva
from user.models import User


class Pago(models.Model):

    METODOS = (
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('mercado_pago', 'Mercado Pago'),
        ('creditos', 'Créditos'),
    )

    ESTADOS = (
        ('pendiente', 'Pendiente'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
        ('reembolsado', 'Reembolsado'),
    )

    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        related_name='pagos'
    )

    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    metodo_pago = models.CharField(
        max_length=30,
        choices=METODOS
    )

    estado_pago = models.CharField(
        max_length=30,
        choices=ESTADOS,
        default='pendiente'
    )

    fecha_pago = models.DateTimeField(auto_now_add=True)

    referencia_mp = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    registrado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return f"Pago #{self.id}"